from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from datetime import date

from app.database.connection import get_db
from app.database.schemas import User, QuestionnaireResponse, WeatherSnapshot
from app.services.farm_service import get_user_farm
from app.services.weather_service import weather_service
from app.utils.auth_utils import get_current_user
from app.utils.rate_limit import limiter, user_or_ip

router = APIRouter()


def _snapshot_to_current(snapshot: WeatherSnapshot):
    raw = snapshot.raw_json or {}
    if isinstance(raw, dict) and raw.get("current"):
        return raw["current"]
    return {
        "temperature": snapshot.temp,
        "humidity": snapshot.humidity,
        "pressure": raw.get("pressure", 0) if isinstance(raw, dict) else 0,
        "wind_speed": raw.get("wind_speed", 0) if isinstance(raw, dict) else 0,
        "description": raw.get("description", "cached") if isinstance(raw, dict) else "cached",
        "visibility": raw.get("visibility", 0) if isinstance(raw, dict) else 0,
        "location": raw.get("location", "Farm Location") if isinstance(raw, dict) else "Farm Location",
        "_source": snapshot.source,
    }


def _snapshot_to_overview(snapshot: WeatherSnapshot):
    raw = snapshot.raw_json or {}
    if isinstance(raw, dict) and raw.get("current"):
        return {
            "current": raw["current"],
            "forecast": raw.get("forecast", []),
            "location": raw.get("location") or raw["current"].get("location"),
        }
    current = _snapshot_to_current(snapshot)
    return {
        "current": current,
        "forecast": [],
        "location": current.get("location"),
    }


def _get_today_snapshot(db: Session, farm_id: int):
    return (
        db.query(WeatherSnapshot)
        .filter(WeatherSnapshot.farm_id == farm_id, WeatherSnapshot.date == date.today())
        .first()
    )


def _save_weather_snapshot(db: Session, farm_id: int, current: dict, forecast: dict | None = None):
    source = current.get("_source") or (forecast or {}).get("_source") or "unknown"
    forecast_items = (forecast or {}).get("forecast", [])
    # A count of rainy forecast entries is not a rainfall measurement.
    rainfall_mm = None

    snapshot = WeatherSnapshot(
        farm_id=farm_id,
        date=date.today(),
        source=source,
        temp=current.get("temperature"),
        humidity=current.get("humidity"),
        rainfall_mm=rainfall_mm,
        raw_json={
            "current": current,
            "forecast": forecast_items,
            "location": current.get("location") or (forecast or {}).get("location"),
        },
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def _get_user_location(db: Session, user_id: int, farm_id: int):
    env_response = (
        db.query(QuestionnaireResponse)
        .filter(
            QuestionnaireResponse.user_id == user_id,
            QuestionnaireResponse.farm_id == farm_id,
            QuestionnaireResponse.set_number == 4,
        )
        .order_by(QuestionnaireResponse.updated_at.desc())
        .first()
    )

    if not env_response or not env_response.answers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location data not found. Please complete questionnaire set 4.",
        )

    answers = env_response.answers
    city = (
        answers.get("district")
        or answers.get("city")
        or answers.get("village")
        or "Delhi"
    )
    state = answers.get("state") or "Delhi"
    return city, state


@router.get("/current")
@limiter.limit("60/minute", key_func=user_or_ip)
async def get_current_weather(
    request: Request,
    farm_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farm = get_user_farm(db, current_user, farm_id)
    db.commit()

    snapshot = _get_today_snapshot(db, farm.id)
    if snapshot:
        return _snapshot_to_current(snapshot)

    city, state = _get_user_location(db, current_user.id, farm.id)
    data = await weather_service.get_current_weather(city=city, state=state)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to fetch weather data",
        )

    _save_weather_snapshot(db, farm.id, data)
    return data


@router.get("/forecast")
@limiter.limit("60/minute", key_func=user_or_ip)
async def get_weather_forecast(
    request: Request,
    farm_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farm = get_user_farm(db, current_user, farm_id)
    db.commit()

    city, state = _get_user_location(db, current_user.id, farm.id)
    data = await weather_service.get_weather_forecast(city=city, state=state)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to fetch weather forecast",
        )

    return data


@router.get("/overview")
@limiter.limit("60/minute", key_func=user_or_ip)
async def get_weather_overview(
    request: Request,
    farm_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farm = get_user_farm(db, current_user, farm_id)
    db.commit()

    snapshot = _get_today_snapshot(db, farm.id)
    if snapshot:
        return _snapshot_to_overview(snapshot)

    city, state = _get_user_location(db, current_user.id, farm.id)
    current = await weather_service.get_current_weather(city=city, state=state)
    forecast = await weather_service.get_weather_forecast(city=city, state=state)

    if not current or not forecast:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to fetch weather overview",
        )

    _save_weather_snapshot(db, farm.id, current, forecast)
    return {
        "current": current,
        "forecast": forecast.get("forecast", []),
        "location": current.get("location") or forecast.get("location") or f"{city}, {state}",
    }
