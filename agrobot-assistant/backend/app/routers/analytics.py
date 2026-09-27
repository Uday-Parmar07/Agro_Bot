from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.schemas import User
from app.models.analytics import AnalyticsOverviewResponse
from app.services.analytics_service import build_analytics_overview
from app.services.farm_service import get_user_farm
from app.utils.auth_utils import get_current_user

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
