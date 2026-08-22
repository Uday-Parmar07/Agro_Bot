from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.schemas import FarmCrop, HarvestOutcome, User
from app.models.finance import HarvestOutcomeCreate, HarvestOutcomeResponse
from app.utils.auth_utils import get_current_user

router = APIRouter()


@router.post("", response_model=HarvestOutcomeResponse)
async def create_harvest_outcome(
    payload: HarvestOutcomeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crop = (
        db.query(FarmCrop)
        .join(FarmCrop.farm)
        .filter(FarmCrop.id == payload.farm_crop_id, FarmCrop.farm.has(user_id=current_user.id))
        .first()
    )
    if not crop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crop not found")
    outcome = HarvestOutcome(**payload.model_dump())
    db.add(outcome)
    crop.status = "harvested"
    db.commit()
    db.refresh(outcome)
    return outcome
