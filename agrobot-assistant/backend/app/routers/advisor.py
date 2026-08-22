from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.schemas import AdvisorFarmerLink, DiseasePrediction, Farm, Recommendation, User, WeatherSnapshot
from app.models.advisor import AdvisorFarmerItem, AdvisorFarmerSummary
from app.utils.auth_utils import require_role

router = APIRouter()


def _assigned_farmer_ids(db: Session, advisor_id: int) -> list[int]:
    return [
        row.farmer_id
        for row in db.query(AdvisorFarmerLink)
        .filter(AdvisorFarmerLink.advisor_id == advisor_id)
        .all()
    ]


@router.get("/farmers", response_model=list[AdvisorFarmerItem])
async def list_assigned_farmers(
    current_user: User = Depends(require_role("advisor", "admin")),
    db: Session = Depends(get_db),
):
    farmer_ids = _assigned_farmer_ids(db, current_user.id)
    if current_user.role == "admin" and not farmer_ids:
        farmer_ids = [user.id for user in db.query(User).filter(User.role == "farmer").all()]

    cutoff = datetime.utcnow() - timedelta(days=30)
    items = []
    for farmer in db.query(User).filter(User.id.in_(farmer_ids)).all() if farmer_ids else []:
        farms = db.query(Farm).filter(Farm.user_id == farmer.id).all()
        farm_ids = [farm.id for farm in farms]
        latest_rec = (
            db.query(Recommendation)
            .filter(Recommendation.farm_id.in_(farm_ids))
            .order_by(Recommendation.generated_at.desc())
            .first()
            if farm_ids else None
        )
        disease_count = (
            db.query(DiseasePrediction)
            .filter(DiseasePrediction.farm_id.in_(farm_ids), DiseasePrediction.created_at >= cutoff)
            .count()
            if farm_ids else 0
        )
        items.append(AdvisorFarmerItem(
            farmer_id=farmer.id,
            full_name=farmer.full_name,
            email=farmer.email,
            farms_count=len(farms),
            latest_soil_score=latest_rec.soil_health_score if latest_rec else None,
            disease_checks_30d=disease_count,
        ))
    return items


@router.get("/farmers/{farmer_id}/summary", response_model=AdvisorFarmerSummary)
async def get_farmer_summary(
    farmer_id: int,
    current_user: User = Depends(require_role("advisor", "admin")),
    db: Session = Depends(get_db),
):
    if current_user.role != "admin" and farmer_id not in _assigned_farmer_ids(db, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Farmer is not assigned")

    farmer = db.query(User).filter(User.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farmer not found")

    farms = db.query(Farm).filter(Farm.user_id == farmer_id).all()
    farm_ids = [farm.id for farm in farms]
    latest_rec = (
        db.query(Recommendation)
        .filter(Recommendation.farm_id.in_(farm_ids))
        .order_by(Recommendation.generated_at.desc())
        .first()
        if farm_ids else None
    )
    disease_predictions = (
        db.query(DiseasePrediction)
        .filter(DiseasePrediction.farm_id.in_(farm_ids))
        .order_by(DiseasePrediction.created_at.desc())
        .all()
        if farm_ids else []
    )
    disease_flags = [
        pred.predicted_class for pred in disease_predictions
        if "healthy" not in pred.predicted_class.lower()
    ][:10]
    weather_count = (
        db.query(WeatherSnapshot).filter(WeatherSnapshot.farm_id.in_(farm_ids)).count()
        if farm_ids else 0
    )
    return AdvisorFarmerSummary(
        farmer_id=farmer.id,
        full_name=farmer.full_name,
        email=farmer.email,
        latest_soil_score=latest_rec.soil_health_score if latest_rec else None,
        disease_checks=len(disease_predictions),
        disease_flags=disease_flags,
        weather_snapshots=weather_count,
        last_recommendation_at=latest_rec.generated_at if latest_rec else None,
    )
