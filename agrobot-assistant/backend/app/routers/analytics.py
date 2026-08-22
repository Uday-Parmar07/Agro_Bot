from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.schemas import User
from app.models.analytics import AnalyticsOverviewResponse
from app.models.finance import ProfitabilityItem, ProfitabilityResponse
from app.services.analytics_service import build_analytics_overview
from app.services.farm_service import get_user_farm
from app.utils.auth_utils import get_current_user
from app.database.schemas import FarmCrop, HarvestOutcome, Recommendation

router = APIRouter()


@router.get("/overview", response_model=AnalyticsOverviewResponse)
async def get_analytics_overview(
    farm_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farm = get_user_farm(db, current_user, farm_id)
    db.commit()
    return build_analytics_overview(db, farm.id)


@router.get("/profitability", response_model=ProfitabilityResponse)
async def get_profitability(
    farm_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farm = get_user_farm(db, current_user, farm_id)
    db.commit()

    latest_rec = (
        db.query(Recommendation)
        .filter(Recommendation.farm_id == farm.id)
        .order_by(Recommendation.generated_at.desc())
        .first()
    )
    predicted = {}
    if latest_rec and latest_rec.recommended_crops:
        predicted = {
            crop.get("crop_name", "").strip().lower(): crop.get("profitability_score")
            for crop in latest_rec.recommended_crops
        }

    outcomes = (
        db.query(HarvestOutcome, FarmCrop)
        .join(FarmCrop, HarvestOutcome.farm_crop_id == FarmCrop.id)
        .filter(FarmCrop.farm_id == farm.id)
        .all()
    )
    return ProfitabilityResponse(
        farm_id=farm.id,
        outcomes=[
            ProfitabilityItem(
                crop_name=crop.crop_name,
                realized_revenue=round(outcome.actual_yield * outcome.sale_price_per_unit, 2),
                predicted_profitability_score=predicted.get(crop.crop_name.strip().lower()),
            )
            for outcome, crop in outcomes
        ],
    )
