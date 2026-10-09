import asyncio
import os
import tempfile
import uuid
from datetime import date, timedelta

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.gettempdir()}/agrobot_mandi_test_{uuid.uuid4().hex}.db"
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("AGMARKNET_API_KEY", "test-key")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import httpx

from app.database.schemas import Base, CropMarketNews, Mandi, MandiPriceSnapshot
from app.services import crop_news_service as news_module
from app.services.crop_news_service import CropNewsService
from app.services.mandi_price_service import (
    MandiPriceService,
    calculate_trend,
    calculate_trip_gain,
)
from app.main import app


def _db_session():
    engine = create_engine(f"sqlite:///{tempfile.gettempdir()}/agrobot_mandi_unit_{uuid.uuid4().hex}.db")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


async def test_cache_first_fetch_does_not_rehit_api():
    db = _db_session()
    service = MandiPriceService()
    calls = []
    today = date.today()

    async def fake_fetch_prices(**kwargs):
        calls.append(kwargs)
        return [
            {
                "commodity": "Tomato",
                "market_name": "Pune",
                "state": "Maharashtra",
                "district": "Pune",
                "min_price": 1100.0,
                "max_price": 1300.0,
                "modal_price": 1200.0,
                "arrival_qty": 50.0,
                "price_date": today,
            }
        ]

    service.fetch_prices = fake_fetch_prices
    first = await service.get_cached_or_fetch(db, "Tomato", "Pune", today)
    second = await service.get_cached_or_fetch(db, "Tomato", "Pune", today)

    assert first.id == second.id
    assert second.modal_price == 1200.0
    assert len(calls) == 1
    assert db.query(MandiPriceSnapshot).count() == 1


async def test_missing_today_falls_back_to_recent_report_date():
    db = _db_session()
    service = MandiPriceService()
    calls = []
    today = date.today()
    yesterday = today - timedelta(days=1)

    async def fake_fetch_prices(**kwargs):
        calls.append(kwargs["date_value"])
        if kwargs["date_value"] == today:
            return []
        return [
            {
                "commodity": "Onion",
                "market_name": "Lasalgaon",
                "state": "Maharashtra",
                "district": "Nashik",
                "min_price": 1800.0,
                "max_price": 2200.0,
                "modal_price": 2050.0,
                "arrival_qty": 80.0,
                "price_date": yesterday,
            }
        ]

    service.fetch_prices = fake_fetch_prices
    snapshot = await service.get_cached_or_fetch(db, "Onion", "Lasalgaon", today)

    assert snapshot is not None
    assert snapshot.price_date == yesterday
    assert snapshot.modal_price == 2050.0
    assert calls == [today, yesterday]


async def test_current_prices_falls_back_to_recent_state_market_when_nearest_has_no_data():
    db = _db_session()
    service = MandiPriceService()
    farm = type("FarmLike", (), {
        "id": 1,
        "location": "Datia, Madhya Pradesh",
        "latitude": 25.6653,
        "longitude": 78.4609,
    })()

    db.add(
        Mandi(
            market_name="Indore",
            state="Madhya Pradesh",
            district="Indore",
            latitude=22.7196,
            longitude=75.8577,
        )
    )
    db.commit()

    async def fake_get_cached_or_fetch(db, commodity, market, date_value=None, state=None, lookback_days=7):
        return None

    async def fake_fetch_recent_scope_snapshots(db, commodity, state=None, date_value=None, lookback_days=7, limit=250):
        return [
            MandiPriceSnapshot(
                commodity=commodity,
                market_name="Neemuch",
                state=state,
                district="Neemuch",
                modal_price=2210.0,
                min_price=2100.0,
                max_price=2300.0,
                price_date=date.today() - timedelta(days=1),
            )
        ]

    async def fake_summary_for_scope(db, commodity, state=None):
        return {
            "modal_price": 2210.0,
            "market_count": 1,
            "price_date": date.today() - timedelta(days=1),
            "data_status": "available",
        }

    service.get_cached_or_fetch = fake_get_cached_or_fetch
    service.fetch_recent_scope_snapshots = fake_fetch_recent_scope_snapshots
    service._summary_for_scope = fake_summary_for_scope

    result = await service.get_current_prices(db, farm, "Maize", ["Maize"])

    assert result["nearby"][0]["market_name"] == "Neemuch"
    assert result["nearby"][0]["modal_price"] == 2210.0
    assert result["primary_market"] == "Neemuch"


def test_trip_gain_worked_examples():
    clearly_worth = calculate_trip_gain(
        baseline_price=1000,
        candidate_price=1300,
        expected_quantity_quintals=20,
        distance_km=50,
        transport_cost_per_km=20,
        threshold=500,
    )
    clearly_not_worth = calculate_trip_gain(
        baseline_price=1000,
        candidate_price=1040,
        expected_quantity_quintals=10,
        distance_km=80,
        transport_cost_per_km=20,
        threshold=500,
    )
    borderline = calculate_trip_gain(
        baseline_price=1000,
        candidate_price=1080,
        expected_quantity_quintals=20,
        distance_km=50,
        transport_cost_per_km=20,
        threshold=600,
    )

    assert clearly_worth["net_gain"] == 5000
    assert clearly_worth["worth_trip"] is True
    assert clearly_not_worth["net_gain"] == -1200
    assert clearly_not_worth["worth_trip"] is False
    assert borderline["net_gain"] == 600
    assert borderline["worth_trip"] is False


def test_trend_direction_calculation():
    base = date.today() - timedelta(days=2)
    up = calculate_trend([
        {"date": base, "modal_price": 1000},
        {"date": base + timedelta(days=1), "modal_price": 1100},
    ])
    down = calculate_trend([
        {"date": base, "modal_price": 1000},
        {"date": base + timedelta(days=1), "modal_price": 900},
    ])
    stable = calculate_trend([
        {"date": base, "modal_price": 1000},
        {"date": base + timedelta(days=1), "modal_price": 1005},
    ])
    no_data = calculate_trend([{"date": base, "modal_price": None}])

    assert up["direction"] == "up"
    assert down["direction"] == "down"
    assert stable["direction"] == "stable"
    assert no_data["direction"] == "no_data"


async def test_compare_mandis_only_returns_threshold_positive_options():
    db = _db_session()
    service = MandiPriceService()
    farm = type("FarmLike", (), {
        "id": 1,
        "location": "Pune, Maharashtra",
        "latitude": 18.5204,
        "longitude": 73.8567,
    })()
    crop = type("CropLike", (), {"crop_name": "Tomato", "area_acres": 2})()

    db.add_all([
        Mandi(market_name="Pune", state="Maharashtra", district="Pune", latitude=18.5204, longitude=73.8567),
        Mandi(market_name="Nashik", state="Maharashtra", district="Nashik", latitude=19.9975, longitude=73.7898),
        Mandi(market_name="Mumbai", state="Maharashtra", district="Mumbai", latitude=19.0760, longitude=72.8777),
    ])
    db.commit()

    async def fake_get_cached_or_fetch(db, commodity, market, date_value=None, state=None, lookback_days=7):
        prices = {"Pune": 1000.0, "Nashik": 1600.0, "Mumbai": 1010.0}
        return MandiPriceSnapshot(
            commodity=commodity,
            market_name=market,
            state=state,
            district=market,
            modal_price=prices[market],
            price_date=date.today(),
        )

    service.get_cached_or_fetch = fake_get_cached_or_fetch
    result = await service.compare_mandis(db, farm, crop, radius_km=250)

    assert [item["market_name"] for item in result["recommendations"]] == ["Nashik"]
    assert result["recommendations"][0]["net_gain"] > result["threshold"]
    assert result["best_candidate"]["market_name"] == "Nashik"


async def test_compare_mandis_returns_exactly_one_qualifier():
    db = _db_session()
    service = MandiPriceService()
    farm = type("FarmLike", (), {
        "id": 1,
        "location": "Pune, Maharashtra",
        "latitude": 18.5204,
        "longitude": 73.8567,
    })()
    crop = type("CropLike", (), {"crop_name": "Tomato", "area_acres": 2})()

    db.add_all([
        Mandi(market_name="Pune", state="Maharashtra", district="Pune", latitude=18.5204, longitude=73.8567),
        Mandi(market_name="Nashik", state="Maharashtra", district="Nashik", latitude=19.9975, longitude=73.7898),
        Mandi(market_name="Mumbai", state="Maharashtra", district="Mumbai", latitude=19.0760, longitude=72.8777),
    ])
    db.commit()

    async def fake_get_cached_or_fetch(db, commodity, market, date_value=None, state=None, lookback_days=7):
        prices = {"Pune": 1000.0, "Nashik": 1500.0, "Mumbai": 1015.0}
        return MandiPriceSnapshot(
            commodity=commodity,
            market_name=market,
            state=state,
            district=market,
            modal_price=prices[market],
            price_date=date.today(),
        )

    service.get_cached_or_fetch = fake_get_cached_or_fetch
    result = await service.compare_mandis(db, farm, crop, radius_km=250)

    assert len(result["recommendations"]) == 1
    assert result["recommendations"][0]["market_name"] == "Nashik"
    assert result["best_candidate"]["market_name"] == "Nashik"


async def test_compare_mandis_caps_to_top_three_sorted_by_net_gain():
    db = _db_session()
    service = MandiPriceService()
    farm = type("FarmLike", (), {
        "id": 1,
        "location": "Pune, Maharashtra",
        "latitude": 18.5204,
        "longitude": 73.8567,
    })()
    crop = type("CropLike", (), {"crop_name": "Tomato", "area_acres": 4})()

    db.add_all([
        Mandi(market_name="Pune", state="Maharashtra", district="Pune", latitude=18.5204, longitude=73.8567),
        Mandi(market_name="Nashik", state="Maharashtra", district="Nashik", latitude=19.9975, longitude=73.7898),
        Mandi(market_name="Mumbai", state="Maharashtra", district="Mumbai", latitude=19.0760, longitude=72.8777),
        Mandi(market_name="Ahmednagar", state="Maharashtra", district="Ahmednagar", latitude=19.0952, longitude=74.7496),
        Mandi(market_name="Satara", state="Maharashtra", district="Satara", latitude=17.6805, longitude=74.0183),
        Mandi(market_name="Nagpur", state="Maharashtra", district="Nagpur", latitude=21.1458, longitude=79.0882),
    ])
    db.commit()

    prices = {
        "Pune": 1000.0,
        "Nashik": 1420.0,
        "Mumbai": 1500.0,
        "Ahmednagar": 1450.0,
        "Satara": 1550.0,
        "Nagpur": 1600.0,
    }

    async def fake_get_cached_or_fetch(db, commodity, market, date_value=None, state=None, lookback_days=7):
        return MandiPriceSnapshot(
            commodity=commodity,
            market_name=market,
            state=state,
            district=market,
            modal_price=prices[market],
            price_date=date.today(),
        )

    service.get_cached_or_fetch = fake_get_cached_or_fetch
    result = await service.compare_mandis(db, farm, crop, radius_km=1000)
    recommendations = result["recommendations"]

    assert len(recommendations) == 3
    assert [item["net_gain"] for item in recommendations] == sorted(
        [item["net_gain"] for item in recommendations],
        reverse=True,
    )
    assert result["best_candidate"] == recommendations[0]


async def test_compare_mandis_empty_when_no_market_clears_threshold():
    db = _db_session()
    service = MandiPriceService()
    farm = type("FarmLike", (), {
        "id": 1,
        "location": "Pune, Maharashtra",
        "latitude": 18.5204,
        "longitude": 73.8567,
    })()
    crop = type("CropLike", (), {"crop_name": "Tomato", "area_acres": 1})()

    db.add_all([
        Mandi(market_name="Pune", state="Maharashtra", district="Pune", latitude=18.5204, longitude=73.8567),
        Mandi(market_name="Mumbai", state="Maharashtra", district="Mumbai", latitude=19.0760, longitude=72.8777),
    ])
    db.commit()

    async def fake_get_cached_or_fetch(db, commodity, market, date_value=None, state=None, lookback_days=7):
        prices = {"Pune": 1000.0, "Mumbai": 1020.0}
        return MandiPriceSnapshot(
            commodity=commodity,
            market_name=market,
            state=state,
            district=market,
            modal_price=prices[market],
            price_date=date.today(),
        )

    service.get_cached_or_fetch = fake_get_cached_or_fetch
    result = await service.compare_mandis(db, farm, crop, radius_km=250)

    assert result["recommendations"] == []
    assert result["best_candidate"] is None


class _FakeTavily:
    def __init__(self):
        self.calls = 0

    def search(self, **kwargs):
        self.calls += 1
        return {
            "results": [
                {
                    "title": "Tomato arrivals fall in major mandis",
                    "url": "https://pib.gov.in/tomato-market",
                    "content": "Tomato mandi arrivals declined after heavy rain, supporting prices.",
                    "published_date": date.today().isoformat(),
                }
            ]
        }


class _FakeGroq:
    def __init__(self):
        self.calls = 0
        self.chat = type("Chat", (), {})()
        self.chat.completions = self

    def create(self, **kwargs):
        self.calls += 1
        message = type("Message", (), {
            "content": (
                '{"insights":[{"headline":"Lower tomato arrivals support prices",'
                '"summary":"Heavy rain reduced mandi arrivals, which can support tomato prices.",'
                '"source_url":"https://pib.gov.in/tomato-market"}]}'
            )
        })()
        choice = type("Choice", (), {"message": message})()
        return type("Completion", (), {"choices": [choice]})()


def test_crop_market_news_cache_first_does_not_recall_tavily_or_groq():
    db = _db_session()
    service = CropNewsService()
    fake_tavily = _FakeTavily()
    fake_groq = _FakeGroq()
    original_tavily = news_module.government_api_service.tavily
    original_groq = news_module.government_api_service.groq_client

    try:
        news_module.government_api_service.tavily = fake_tavily
        news_module.government_api_service.groq_client = fake_groq
        first = service.get_or_fetch_news(db, "Tomato", date.today())
        second = service.get_or_fetch_news(db, "Tomato", date.today())
    finally:
        news_module.government_api_service.tavily = original_tavily
        news_module.government_api_service.groq_client = original_groq

    assert len(first["insights"]) == 1
    assert len(second["insights"]) == 1
    assert fake_tavily.calls == 2
    assert fake_groq.calls == 1
    assert db.query(CropMarketNews).count() == 1


def test_crop_market_news_empty_state_is_cached():
    db = _db_session()
    service = CropNewsService()
    fake_tavily = _FakeTavily()
    fake_groq = _FakeGroq()

    def empty_search(**kwargs):
        fake_tavily.calls += 1
        return {"results": []}

    fake_tavily.search = empty_search
    original_tavily = news_module.government_api_service.tavily
    original_groq = news_module.government_api_service.groq_client

    try:
        news_module.government_api_service.tavily = fake_tavily
        news_module.government_api_service.groq_client = fake_groq
        first = service.get_or_fetch_news(db, "Soybean", date.today())
        second = service.get_or_fetch_news(db, "Soybean", date.today())
    finally:
        news_module.government_api_service.tavily = original_tavily
        news_module.government_api_service.groq_client = original_groq

    assert first["insights"] == []
    assert second["insights"] == []
    assert first["data_status"] == "no_news"
    assert fake_tavily.calls == 2
    assert fake_groq.calls == 0
    assert db.query(CropMarketNews).count() == 1


async def _auth_headers(client: httpx.AsyncClient):
    email = f"mandi-lookup-{uuid.uuid4().hex}@example.com"
    signup = await client.post(
        "/api/auth/signup",
        json={
            "email": email,
            "password": "lookup-password",
            "full_name": "Lookup Farmer",
            "phone_number": "9999999999",
        },
    )
    signup.raise_for_status()
    return {"Authorization": f"Bearer {signup.json()['access_token']}"}


async def test_mandi_lookup_endpoints_return_cached_locations_and_commodities():
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            headers = await _auth_headers(client)
            locations = await client.get("/api/mandi-prices/locations", headers=headers)
            locations.raise_for_status()
            assert any(item["market_name"] == "Pune" for item in locations.json()["locations"])

            filtered = await client.get(
                "/api/mandi-prices/locations",
                params={"state": "Maharashtra", "district": "Pune"},
                headers=headers,
            )
            filtered.raise_for_status()
            assert all(item["state"] == "Maharashtra" for item in filtered.json()["locations"])

            commodities = await client.get(
                "/api/mandi-prices/commodities",
                params={"q": "tom"},
                headers=headers,
            )
            commodities.raise_for_status()
            assert "Tomato" in commodities.json()["commodities"]


if __name__ == "__main__":
    asyncio.run(test_cache_first_fetch_does_not_rehit_api())
    asyncio.run(test_missing_today_falls_back_to_recent_report_date())
    asyncio.run(test_current_prices_falls_back_to_recent_state_market_when_nearest_has_no_data())
    test_trip_gain_worked_examples()
    test_trend_direction_calculation()
    asyncio.run(test_compare_mandis_only_returns_threshold_positive_options())
    asyncio.run(test_compare_mandis_returns_exactly_one_qualifier())
    asyncio.run(test_compare_mandis_caps_to_top_three_sorted_by_net_gain())
    asyncio.run(test_compare_mandis_empty_when_no_market_clears_threshold())
    test_crop_market_news_cache_first_does_not_recall_tavily_or_groq()
    test_crop_market_news_empty_state_is_cached()
    asyncio.run(test_mandi_lookup_endpoints_return_cached_locations_and_commodities())
    print("Mandi price service tests passed")
