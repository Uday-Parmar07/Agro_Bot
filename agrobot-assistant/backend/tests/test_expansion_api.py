import asyncio
import os
import tempfile
import uuid

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.gettempdir()}/agrobot_expansion_api_test_{uuid.uuid4().hex}.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import httpx

from app.database.connection import SessionLocal
from app.database.schemas import AdvisorFarmerLink, User
from app.main import app


async def _signup(client: httpx.AsyncClient, email: str, password: str = "password"):
    response = await client.post(
        "/api/auth/signup",
        json={
            "email": email,
            "password": password,
            "full_name": email.split("@")[0].title(),
            "phone_number": "9999999999",
        },
    )
    response.raise_for_status()
    return response.json()


async def _complete_questionnaire(client: httpx.AsyncClient, headers: dict):
    me = await client.get("/api/auth/me", headers=headers)
    me.raise_for_status()
    user_id = me.json()["id"]
    response = await client.post(
        "/api/questionnaire/complete",
        json={
            "user_id": user_id,
            "soil_physical": {"soil_texture": "loamy", "water_retention": "moderate", "soil_top_layer": "dark_crumbly"},
            "soil_fertility": {"soil_test_done": False, "yellowing_slow_growth": False, "fertilizer_type": "organic"},
            "moisture_irrigation": {"irrigation_type": "drip", "watering_frequency": "weekly"},
            "environmental": {"state": "Maharashtra", "district": "Pune", "total_area": 2, "area_unit": "acre"},
            "organic_practices": {"uses_organic_matter": True, "organic_matter_types": ["compost"], "crop_residue_practice": "leave_in_field", "earthworms_present": True},
        },
        headers=headers,
    )
    response.raise_for_status()


def _set_role_and_link(advisor_email: str, farmer_email: str):
    db = SessionLocal()
    try:
        advisor = db.query(User).filter(User.email == advisor_email).first()
        farmer = db.query(User).filter(User.email == farmer_email).first()
        advisor.role = "advisor"
        db.add(AdvisorFarmerLink(advisor_id=advisor.id, farmer_id=farmer.id))
        db.commit()
    finally:
        db.close()


async def test_expansion_endpoints():
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            farmer = await _signup(client, "farmer@example.com")
            advisor = await _signup(client, "advisor@example.com")
            farmer_headers = {"Authorization": f"Bearer {farmer['access_token']}"}
            advisor_headers = {"Authorization": f"Bearer {advisor['access_token']}"}

            _set_role_and_link("advisor@example.com", "farmer@example.com")
            await _complete_questionnaire(client, farmer_headers)

            language = await client.patch("/api/users/me/language", json={"preferred_language": "hi"}, headers=farmer_headers)
            language.raise_for_status()
            assert language.json()["preferred_language"] == "hi"

            voice = await client.post(
                "/api/voice/transcribe",
                files={"audio": ("voice.webm", b"fake-audio", "audio/webm")},
                headers=farmer_headers,
            )
            voice.raise_for_status()
            assert "transcript" in voice.json()

            farms = await client.get("/api/farms", headers=farmer_headers)
            farms.raise_for_status()
            farm_id = farms.json()[0]["id"]

            crop = await client.post(
                "/api/dashboard/crops",
                json={"farm_id": farm_id, "crop_name": "Tomato", "area_acres": 1},
                headers=farmer_headers,
            )
            crop.raise_for_status()
            crop_id = crop.json()["id"]

            scheme = await client.post(
                "/api/schemes/0/save",
                json={"farm_id": farm_id, "scheme_name": "Test Scheme", "summary": "Useful scheme"},
                headers=farmer_headers,
            )
            scheme.raise_for_status()
            record_id = scheme.json()["id"]
            patched_scheme = await client.patch(
                f"/api/schemes/records/{record_id}",
                json={"status": "applied", "notes": "Submitted"},
                headers=farmer_headers,
            )
            patched_scheme.raise_for_status()
            assert patched_scheme.json()["status"] == "applied"

            harvest = await client.post(
                "/api/harvest-outcomes",
                json={"farm_crop_id": crop_id, "actual_yield": 100, "unit": "kg", "sale_price_per_unit": 20, "harvested_at": "2026-08-23"},
                headers=farmer_headers,
            )
            harvest.raise_for_status()
            profitability = await client.get(f"/api/analytics/profitability?farm_id={farm_id}", headers=farmer_headers)
            profitability.raise_for_status()
            assert profitability.json()["outcomes"][0]["realized_revenue"] == 2000

            listing = await client.post(
                "/api/marketplace/listings",
                json={"crop_name": "Tomato", "quantity": 50, "unit": "kg", "price": 30, "location": "Pune"},
                headers=farmer_headers,
            )
            listing.raise_for_status()
            listings = await client.get("/api/marketplace/listings", headers=farmer_headers)
            listings.raise_for_status()
            assert len(listings.json()) >= 1

            post = await client.post(
                "/api/forum/posts",
                json={"region": "Pune", "crop_tag": "tomato", "title": "Leaf spot?", "body": "Anyone seeing this?"},
                headers=farmer_headers,
            )
            post.raise_for_status()
            post_id = post.json()["id"]
            reply = await client.post(
                f"/api/forum/posts/{post_id}/replies",
                json={"body": "Yes, check humidity."},
                headers=farmer_headers,
            )
            reply.raise_for_status()
            report = await client.post(
                "/api/reports",
                json={"target_type": "post", "target_id": post_id, "reason": "test"},
                headers=farmer_headers,
            )
            report.raise_for_status()

            advisor_list = await client.get("/api/advisor/farmers", headers=advisor_headers)
            advisor_list.raise_for_status()
            assert advisor_list.json()[0]["email"] == "farmer@example.com"


if __name__ == "__main__":
    asyncio.run(test_expansion_endpoints())
    print("Expansion API smoke test passed")
