from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.schemas import Farm, User
from app.models.farm import FarmCreate, FarmResponse
from app.services.farm_service import get_or_create_default_farm
from app.utils.auth_utils import get_current_user

router = APIRouter()


@router.get("", response_model=list[FarmResponse])
async def list_farms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_or_create_default_farm(db, current_user)
    db.commit()
    return (
        db.query(Farm)
        .filter(Farm.user_id == current_user.id)
        .order_by(Farm.id.asc())
        .all()
    )


@router.post("", response_model=FarmResponse)
async def create_farm(
    farm_data: FarmCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farm = Farm(
        user_id=current_user.id,
        name=farm_data.name,
        location=farm_data.location,
        latitude=farm_data.latitude,
        longitude=farm_data.longitude,
        area_acres=farm_data.area_acres,
    )
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm
