from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.schemas import User, QuestionnaireResponse
from app.services.weather_service import weather_service
from app.utils.auth_utils import get_current_user

router = APIRouter()


def _get_user_location(db: Session, user_id: int):
    env_response = (
        db.query(QuestionnaireResponse)
        .filter(
            QuestionnaireResponse.user_id == user_id,
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
async def get_current_weather(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city, state = _get_user_location(db, current_user.id)
    data = await weather_service.get_current_weather(city=city, state=state)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to fetch weather data",
        )

    return data


@router.get("/forecast")
async def get_weather_forecast(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city, state = _get_user_location(db, current_user.id)
    data = await weather_service.get_weather_forecast(city=city, state=state)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to fetch weather forecast",
        )

    return data


@router.get("/overview")
async def get_weather_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city, state = _get_user_location(db, current_user.id)
    current = await weather_service.get_current_weather(city=city, state=state)
    forecast = await weather_service.get_weather_forecast(city=city, state=state)

    if not current or not forecast:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to fetch weather overview",
        )

    return {
        "current": current,
        "forecast": forecast.get("forecast", []),
        "location": current.get("location") or forecast.get("location") or f"{city}, {state}",
    }
