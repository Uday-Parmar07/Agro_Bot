import json
import logging
import math
import os
import subprocess
import time
from datetime import date, datetime, timedelta
from typing import Any, Optional

import httpx
from sqlalchemy.orm import Session

from app.config import (
    AGMARKNET_API_KEY,
    AGMARKNET_BASE_URL,
    AGMARKNET_RESOURCE_ID,
    EXPECTED_QUINTALS_PER_ACRE,
    MANDI_NET_GAIN_THRESHOLD,
    TRANSPORT_COST_PER_KM,
)
from app.database.schemas import Farm, FarmCrop, Mandi, MandiPriceSnapshot


AGMARKNET_COMMODITIES = [
    "Ajwan", "Apple", "Arhar Dal", "Bajra", "Banana", "Barley", "Bengal Gram Dal",
    "Bhindi", "Bitter Gourd", "Black Gram", "Bottle Gourd", "Brinjal", "Cabbage",
    "Capsicum", "Carrot", "Cauliflower", "Chilli", "Coriander", "Cotton", "Cucumber",
    "Garlic", "Ginger", "Gram", "Grapes", "Green Chilli", "Groundnut", "Guar",
    "Jowar", "Lemon", "Lentil", "Maize", "Mango", "Masur Dal", "Moong Dal",
    "Mustard", "Onion", "Orange", "Paddy", "Pearl Millet", "Peas", "Potato",
    "Ragi", "Rice", "Sesamum", "Soybean", "Sugarcane", "Sunflower", "Tomato",
    "Turmeric", "Urad Dal", "Wheat",
]

logger = logging.getLogger(__name__)


class MandiPriceService:
    def __init__(self):
        self.api_key = AGMARKNET_API_KEY
        self.base_url = AGMARKNET_BASE_URL.rstrip("/")
        self.resource_id = AGMARKNET_RESOURCE_ID
        self.timeout = float(os.getenv("AGMARKNET_TIMEOUT_SECONDS", "5"))
        self.failure_backoff_seconds = float(
            os.getenv("AGMARKNET_FAILURE_BACKOFF_SECONDS", "60")
        )
        self.enable_curl_fallback = os.getenv(
            "AGMARKNET_ENABLE_CURL_FALLBACK", "false"
        ).lower() in {"1", "true", "yes"}
        self._circuit_open_until = 0.0

    async def fetch_prices(
        self,
        commodity: str,
        state: Optional[str] = None,
        market: Optional[str] = None,
        date: Optional[date] = None,
        date_value: Optional[date] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        query_date = date_value or date
        if not self.api_key:
            # Market prices are financial data. Never manufacture them when the
            # external source is unconfigured.
            return []
        if time.monotonic() < self._circuit_open_until:
            return []

        params: dict[str, Any] = {
            "api-key": self.api_key,
            "format": "json",
            "limit": limit,
            "offset": 0,
            "fields": "state,district,market,commodity,arrival_date,min_price,max_price,modal_price,arrival_qty",
            "filters[commodity]": commodity,
        }
        if state:
            params["filters[state]"] = state
        if market:
            params["filters[market]"] = market
        if query_date:
            params["filters[arrival_date]"] = query_date.strftime("%d/%m/%Y")

        param_attempts = [params]
        if state:
            keyword_params = dict(params)
            keyword_params.pop("filters[state]", None)
            keyword_params["filters[state.keyword]"] = state
            param_attempts.append(keyword_params)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payloads = []
                last_status = None
                for request_params in param_attempts:
                    response = await client.get(f"{self.base_url}/{self.resource_id}", params=request_params)
                    last_status = response.status_code
                    if response.status_code in (401, 403):
                        self._record_failure(f"HTTP_{response.status_code}")
                        return []
                    if response.status_code != 200:
                        continue
                    payload = response.json()
                    payloads.append(payload)

                    records = payload.get("records", []) if isinstance(payload, dict) else []
                    if records:
                        break
                if not payloads and last_status is not None:
                    self._record_failure(f"HTTP_{last_status}")
                    return []
        except Exception as exc:
            payloads = self._fetch_with_curl(param_attempts) if self.enable_curl_fallback else []
            if not payloads:
                self._record_failure(exc.__class__.__name__)
                return []

        records = []
        for payload in payloads:
            records.extend(payload.get("records", []) if isinstance(payload, dict) else [])
        parsed = [row for row in (self._parse_record(record) for record in records) if row]

        if state:
            parsed = [row for row in parsed if self._same_text(row.get("state"), state)]
        if market:
            parsed = [row for row in parsed if self._same_text(row.get("market_name"), market)]
        return parsed

    def _fetch_with_curl(self, param_attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        payloads = []
        url = f"{self.base_url}/{self.resource_id}"
        for params in param_attempts:
            command = ["curl", "-sS", "--max-time", str(int(self.timeout * 3)), "-G", url]
            for key, value in params.items():
                if value is None:
                    continue
                command.extend(["--data-urlencode", f"{key}={value}"])
            try:
                completed = subprocess.run(command, capture_output=True, text=True, check=False)
            except OSError as exc:
                logger.warning(
                    "Agmarknet curl fallback unavailable error_type=%s",
                    exc.__class__.__name__,
                )
                return payloads

            if completed.returncode != 0:
                continue
            try:
                payload = json.loads(completed.stdout)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and payload.get("error"):
                return payloads

            payloads.append(payload)
            records = payload.get("records", []) if isinstance(payload, dict) else []
            if records:
                break
        return payloads

    def _record_failure(self, reason: str) -> None:
        """Log once, then suppress repeated external calls during the backoff."""
        now = time.monotonic()
        if now < self._circuit_open_until:
            return
        self._circuit_open_until = now + max(1.0, self.failure_backoff_seconds)
        logger.warning(
            "Agmarknet temporarily unavailable reason=%s backoff_seconds=%s",
            reason,
            int(max(1.0, self.failure_backoff_seconds)),
        )

    async def get_cached_or_fetch(
        self,
        db: Session,
        commodity: str,
        market: str,
        date_value: Optional[date] = None,
        state: Optional[str] = None,
        lookback_days: int = 7,
    ) -> Optional[MandiPriceSnapshot]:
        target_date = date_value or date.today()
        cached = self._get_cached(db, commodity, market, target_date)
        if cached:
            return cached

        for offset in range(lookback_days + 1):
            query_date = target_date - timedelta(days=offset)
            rows = await self.fetch_prices(
                commodity=commodity,
                state=state,
                market=market,
                date_value=query_date,
                limit=50,
            )
            saved_rows = self.save_price_rows(db, rows)
            for snapshot in saved_rows:
                if self._same_text(snapshot.market_name, market):
                    db.commit()
                    return snapshot

        return None

    async def fetch_recent_scope_snapshots(
        self,
        db: Session,
        commodity: str,
        state: Optional[str] = None,
        date_value: Optional[date] = None,
        lookback_days: int = 7,
        limit: int = 250,
    ) -> list[MandiPriceSnapshot]:
        target_date = date_value or date.today()
        for offset in range(lookback_days + 1):
            query_date = target_date - timedelta(days=offset)
            rows = await self.fetch_prices(
                commodity=commodity,
                state=state,
                date_value=query_date,
                limit=limit,
            )
            snapshots = self.save_price_rows(db, rows)
            db.commit()
            priced = [snapshot for snapshot in snapshots if snapshot.modal_price is not None]
            if priced:
                return priced

        return []

    async def get_current_prices(
        self,
        db: Session,
        farm: Farm,
        crop_name: str,
        available_crops: list[str],
        nearby_limit: int = 5,
        market: Optional[str] = None,
        state: Optional[str] = None,
        district: Optional[str] = None,
    ) -> dict[str, Any]:
        farm_state = self._farm_state(farm)
        candidates = self._nearest_mandis(db, farm, state=farm_state, limit=nearby_limit)
        nearby = []

        if market:
            selected_mandi = self._find_mandi(db, market=market, state=state, district=district)
            if selected_mandi:
                selected_distance = self._distance_from_farm(farm, selected_mandi)
                candidates = [(selected_mandi, selected_distance)] + [
                    (mandi, distance)
                    for mandi, distance in candidates
                    if mandi.id != selected_mandi.id
                ]

        for mandi, distance_km in candidates:
            snapshot = await self.get_cached_or_fetch(
                db,
                commodity=crop_name,
                market=mandi.market_name,
                state=mandi.state,
            )
            if snapshot:
                nearby.append(self.snapshot_to_point(snapshot, distance_km=distance_km))
            else:
                nearby.append(
                    {
                        "market_name": mandi.market_name,
                        "state": mandi.state,
                        "district": mandi.district,
                        "distance_km": self._round_distance(distance_km),
                        "data_status": f"no recent data for {mandi.market_name}",
                    }
                )

        if not any(item.get("modal_price") is not None for item in nearby):
            fallback_snapshots = await self.fetch_recent_scope_snapshots(
                db,
                commodity=crop_name,
                state=farm_state,
                lookback_days=7,
            )
            if fallback_snapshots:
                fallback_points = []
                for snapshot in fallback_snapshots:
                    distance_km = self._distance_to_point(farm, snapshot.latitude, snapshot.longitude)
                    fallback_points.append((snapshot, distance_km))
                fallback_points.sort(
                    key=lambda item: (
                        item[1] is None,
                        item[1] if item[1] is not None else 999999,
                        item[0].market_name,
                    )
                )
                nearby = [
                    self.snapshot_to_point(snapshot, distance_km=distance_km)
                    for snapshot, distance_km in fallback_points[:nearby_limit]
                ]

        state_summary = await self._summary_for_scope(db, crop_name, state=farm_state)
        india_summary = await self._summary_for_scope(db, crop_name)
        primary_market = nearby[0]["market_name"] if nearby else None

        return {
            "farm_id": farm.id,
            "crop": crop_name,
            "available_crops": available_crops,
            "nearby": nearby,
            "state_summary": state_summary,
            "india_summary": india_summary,
            "primary_market": primary_market,
        }

    def list_locations(
        self,
        db: Session,
        state: Optional[str] = None,
        district: Optional[str] = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        query = db.query(Mandi)
        if state:
            query = query.filter(Mandi.state.ilike(state))
        if district:
            query = query.filter(Mandi.district.ilike(district))
        rows = query.order_by(Mandi.state.asc(), Mandi.district.asc(), Mandi.market_name.asc()).limit(limit).all()
        return [
            {
                "market_name": row.market_name,
                "state": row.state,
                "district": row.district,
                "latitude": row.latitude,
                "longitude": row.longitude,
            }
            for row in rows
        ]

    def search_commodities(self, db: Session, query: str = "", limit: int = 20) -> list[str]:
        normalized_query = (query or "").strip().lower()
        cached = [
            row[0]
            for row in (
                db.query(MandiPriceSnapshot.commodity)
                .distinct()
                .order_by(MandiPriceSnapshot.commodity.asc())
                .limit(500)
                .all()
            )
            if row[0]
        ]
        combined = sorted({*AGMARKNET_COMMODITIES, *cached}, key=lambda item: item.lower())
        if normalized_query:
            combined = [item for item in combined if normalized_query in item.lower()]
        return combined[:limit]

    async def compare_mandis(
        self,
        db: Session,
        farm: Farm,
        crop: FarmCrop | str,
        radius_km: float,
    ) -> dict[str, Any]:
        crop_name = getattr(crop, "crop_name", crop)
        farm_state = self._farm_state(farm)
        candidates = self._nearest_mandis(db, farm, state=farm_state, limit=50)
        expected_quantity = self._expected_quantity_quintals(crop)

        baseline_snapshot = None
        baseline_distance = None
        baseline_mandi = None
        for mandi, distance_km in candidates:
            snapshot = await self.get_cached_or_fetch(db, crop_name, mandi.market_name, state=mandi.state)
            if snapshot and snapshot.modal_price is not None:
                baseline_snapshot = snapshot
                baseline_distance = distance_km
                baseline_mandi = mandi
                break

        recommendations = []
        if baseline_snapshot:
            for mandi, distance_km in candidates:
                if baseline_mandi and mandi.id == baseline_mandi.id:
                    continue
                if distance_km is None or distance_km > radius_km:
                    continue
                snapshot = await self.get_cached_or_fetch(db, crop_name, mandi.market_name, state=mandi.state)
                if not snapshot or snapshot.modal_price is None:
                    continue
                comparison = calculate_trip_gain(
                    baseline_price=baseline_snapshot.modal_price,
                    candidate_price=snapshot.modal_price,
                    expected_quantity_quintals=expected_quantity,
                    distance_km=distance_km,
                    transport_cost_per_km=TRANSPORT_COST_PER_KM,
                    threshold=MANDI_NET_GAIN_THRESHOLD,
                )
                if comparison["worth_trip"]:
                    recommendations.append(
                        {
                            "market_name": mandi.market_name,
                            "state": mandi.state,
                            "district": mandi.district,
                            "distance_km": self._round_distance(distance_km),
                            "modal_price": snapshot.modal_price,
                            "baseline_price": baseline_snapshot.modal_price,
                            "expected_quantity_quintals": expected_quantity,
                            "price_date": snapshot.price_date,
                            **comparison,
                        }
                    )

        recommendations.sort(key=lambda item: item["net_gain"], reverse=True)
        top_recommendations = recommendations[:3]
        return {
            "farm_id": farm.id,
            "crop": crop_name,
            "radius_km": radius_km,
            "baseline_market": self.snapshot_to_point(baseline_snapshot, baseline_distance) if baseline_snapshot else None,
            "recommendations": top_recommendations,
            "best_candidate": top_recommendations[0] if top_recommendations else None,
            "threshold": MANDI_NET_GAIN_THRESHOLD,
            "transport_cost_per_km": TRANSPORT_COST_PER_KM,
        }

    async def get_price_trend(
        self,
        db: Session,
        commodity: str,
        market: str,
        days: int = 30,
    ) -> dict[str, Any]:
        bounded_days = max(7, min(days, 30))
        end_date = date.today()
        start_date = end_date - timedelta(days=bounded_days - 1)

        points = []
        for offset in range(bounded_days):
            day = start_date + timedelta(days=offset)
            snapshot = await self.get_cached_or_fetch(
                db,
                commodity=commodity,
                market=market,
                date_value=day,
                lookback_days=0,
            )
            if snapshot and snapshot.modal_price is not None:
                points.append(
                    {
                        "date": day,
                        "modal_price": snapshot.modal_price,
                        "data_status": "available",
                    }
                )
            else:
                points.append(
                    {
                        "date": day,
                        "modal_price": None,
                        "data_status": f"no recent data for {market}",
                    }
                )

        trend = calculate_trend(points)
        return {
            "market": market,
            "crop": commodity,
            "days": bounded_days,
            "points": points,
            **trend,
        }

    def save_price_rows(self, db: Session, rows: list[dict[str, Any]]) -> list[MandiPriceSnapshot]:
        snapshots = []
        for row in rows:
            if not row.get("market_name") or not row.get("commodity") or not row.get("price_date"):
                continue
            existing = self._get_cached(db, row["commodity"], row["market_name"], row["price_date"])
            if existing:
                snapshot = existing
                for field in (
                    "state",
                    "district",
                    "min_price",
                    "max_price",
                    "modal_price",
                    "arrival_qty",
                    "latitude",
                    "longitude",
                ):
                    setattr(snapshot, field, row.get(field))
                snapshot.fetched_at = datetime.utcnow()
            else:
                snapshot = MandiPriceSnapshot(
                    commodity=row["commodity"],
                    market_name=row["market_name"],
                    state=row.get("state"),
                    district=row.get("district"),
                    latitude=row.get("latitude"),
                    longitude=row.get("longitude"),
                    min_price=row.get("min_price"),
                    max_price=row.get("max_price"),
                    modal_price=row.get("modal_price"),
                    arrival_qty=row.get("arrival_qty"),
                    price_date=row["price_date"],
                    fetched_at=datetime.utcnow(),
                )
                db.add(snapshot)
            self._upsert_mandi_from_row(db, row)
            db.flush()
            snapshots.append(snapshot)
        return snapshots

    def snapshot_to_point(
        self,
        snapshot: Optional[MandiPriceSnapshot],
        distance_km: Optional[float] = None,
    ) -> Optional[dict[str, Any]]:
        if not snapshot:
            return None
        return {
            "market_name": snapshot.market_name,
            "state": snapshot.state,
            "district": snapshot.district,
            "min_price": snapshot.min_price,
            "max_price": snapshot.max_price,
            "modal_price": snapshot.modal_price,
            "arrival_qty": snapshot.arrival_qty,
            "price_date": snapshot.price_date,
            "fetched_at": snapshot.fetched_at,
            "distance_km": self._round_distance(distance_km),
            "data_status": "available",
        }

    async def _summary_for_scope(
        self,
        db: Session,
        commodity: str,
        state: Optional[str] = None,
    ) -> dict[str, Any]:
        rows = await self.fetch_prices(commodity=commodity, state=state, date_value=date.today(), limit=1000)
        snapshots = self.save_price_rows(db, rows)
        db.commit()
        points = [snap for snap in snapshots if snap.modal_price is not None]

        if not points:
            query = db.query(MandiPriceSnapshot).filter(MandiPriceSnapshot.commodity.ilike(commodity))
            if state:
                query = query.filter(MandiPriceSnapshot.state.ilike(state))
            latest_date = query.order_by(MandiPriceSnapshot.price_date.desc()).first()
            if latest_date:
                query = query.filter(MandiPriceSnapshot.price_date == latest_date.price_date)
                points = [snap for snap in query.all() if snap.modal_price is not None]

        if not points:
            return {"market_count": 0, "data_status": "no_data"}

        modal_values = [point.modal_price for point in points if point.modal_price is not None]
        min_values = [point.min_price for point in points if point.min_price is not None]
        max_values = [point.max_price for point in points if point.max_price is not None]
        latest = max(point.price_date for point in points)
        return {
            "min_price": min(min_values) if min_values else None,
            "max_price": max(max_values) if max_values else None,
            "modal_price": round(sum(modal_values) / len(modal_values), 2) if modal_values else None,
            "market_count": len(points),
            "price_date": latest,
            "data_status": "available",
        }

    def _parse_record(self, record: dict[str, Any]) -> Optional[dict[str, Any]]:
        price_date = self._parse_date(record.get("arrival_date") or record.get("Arrival_Date"))
        if not price_date:
            return None
        return {
            "state": record.get("state"),
            "district": record.get("district"),
            "market_name": record.get("market"),
            "commodity": record.get("commodity"),
            "min_price": self._to_float(record.get("min_price")),
            "max_price": self._to_float(record.get("max_price")),
            "modal_price": self._to_float(record.get("modal_price")),
            "arrival_qty": self._to_float(record.get("arrival_qty") or record.get("arrivals")),
            "price_date": price_date,
        }

    def _get_cached(self, db: Session, commodity: str, market: str, price_date: date) -> Optional[MandiPriceSnapshot]:
        return (
            db.query(MandiPriceSnapshot)
            .filter(
                MandiPriceSnapshot.commodity.ilike(commodity),
                MandiPriceSnapshot.market_name.ilike(market),
                MandiPriceSnapshot.price_date == price_date,
            )
            .first()
        )

    def _nearest_mandis(
        self,
        db: Session,
        farm: Farm,
        state: Optional[str] = None,
        limit: int = 5,
    ) -> list[tuple[Mandi, Optional[float]]]:
        query = db.query(Mandi)
        if state:
            state_rows = query.filter(Mandi.state.ilike(state)).all()
            rows = state_rows if state_rows else query.all()
        else:
            rows = query.all()

        ranked = []
        for mandi in rows:
            distance = None
            if farm.latitude is not None and farm.longitude is not None and mandi.latitude is not None and mandi.longitude is not None:
                distance = haversine_km(farm.latitude, farm.longitude, mandi.latitude, mandi.longitude)
            ranked.append((mandi, distance))

        ranked.sort(key=lambda item: (item[1] is None, item[1] if item[1] is not None else 999999, item[0].market_name))
        return ranked[:limit]

    def _find_mandi(
        self,
        db: Session,
        market: str,
        state: Optional[str] = None,
        district: Optional[str] = None,
    ) -> Optional[Mandi]:
        query = db.query(Mandi).filter(Mandi.market_name.ilike(market))
        if state:
            query = query.filter(Mandi.state.ilike(state))
        if district:
            query = query.filter(Mandi.district.ilike(district))
        return query.order_by(Mandi.state.asc(), Mandi.district.asc()).first()

    def _distance_from_farm(self, farm: Farm, mandi: Mandi) -> Optional[float]:
        if farm.latitude is None or farm.longitude is None or mandi.latitude is None or mandi.longitude is None:
            return None
        return haversine_km(farm.latitude, farm.longitude, mandi.latitude, mandi.longitude)

    def _distance_to_point(
        self,
        farm: Farm,
        latitude: Optional[float],
        longitude: Optional[float],
    ) -> Optional[float]:
        if farm.latitude is None or farm.longitude is None or latitude is None or longitude is None:
            return None
        return haversine_km(farm.latitude, farm.longitude, latitude, longitude)

    def _upsert_mandi_from_row(self, db: Session, row: dict[str, Any]) -> None:
        market_name = row.get("market_name")
        state = row.get("state")
        if not market_name or not state:
            return
        district = row.get("district")
        existing = (
            db.query(Mandi)
            .filter(
                Mandi.market_name.ilike(market_name),
                Mandi.state.ilike(state),
                Mandi.district.ilike(district) if district else Mandi.district.is_(None),
            )
            .first()
        )
        if existing:
            return
        db.add(
            Mandi(
                market_name=market_name,
                state=state,
                district=district,
                latitude=row.get("latitude"),
                longitude=row.get("longitude"),
            )
        )

    def _expected_quantity_quintals(self, crop: FarmCrop | str) -> float:
        area_acres = getattr(crop, "area_acres", None)
        if area_acres:
            return round(max(area_acres * EXPECTED_QUINTALS_PER_ACRE, 1), 2)
        return EXPECTED_QUINTALS_PER_ACRE

    def _farm_state(self, farm: Farm) -> Optional[str]:
        if not farm.location:
            return None
        parts = [part.strip() for part in farm.location.split(",") if part.strip()]
        return parts[-1] if parts else None

    def _parse_date(self, value: Any) -> Optional[date]:
        if isinstance(value, date):
            return value
        if not value:
            return None
        text = str(value).strip()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    def _to_float(self, value: Any) -> Optional[float]:
        if value in (None, "", "NA", "N/A", "-"):
            return None
        try:
            return float(str(value).replace(",", ""))
        except (TypeError, ValueError):
            return None

    def _same_text(self, left: Any, right: Any) -> bool:
        return str(left or "").strip().lower() == str(right or "").strip().lower()

    def _round_distance(self, value: Optional[float]) -> Optional[float]:
        return round(value, 1) if value is not None else None

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def calculate_trip_gain(
    baseline_price: float,
    candidate_price: float,
    expected_quantity_quintals: float,
    distance_km: float,
    transport_cost_per_km: float,
    threshold: float,
) -> dict[str, Any]:
    gross_gain = (candidate_price - baseline_price) * expected_quantity_quintals
    transport_cost = distance_km * transport_cost_per_km
    net_gain = gross_gain - transport_cost
    return {
        "gross_gain": round(gross_gain, 2),
        "transport_cost": round(transport_cost, 2),
        "net_gain": round(net_gain, 2),
        "worth_trip": net_gain > threshold,
    }


def calculate_trend(points: list[dict[str, Any]]) -> dict[str, Any]:
    priced = [point for point in points if point.get("modal_price") is not None]
    if len(priced) < 2:
        return {"direction": "no_data", "change_abs": None, "change_pct": None}

    first = float(priced[0]["modal_price"])
    last = float(priced[-1]["modal_price"])
    change_abs = last - first
    change_pct = (change_abs / first * 100) if first else None
    if change_pct is None or abs(change_pct) < 1:
        direction = "stable"
    elif change_pct > 0:
        direction = "up"
    else:
        direction = "down"
    return {
        "direction": direction,
        "change_abs": round(change_abs, 2),
        "change_pct": round(change_pct, 2) if change_pct is not None else None,
    }


mandi_price_service = MandiPriceService()
