from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.schemas import FarmCrop, User
from app.models.farm_crop import FarmCropCreate, FarmCropResponse, FarmCropUpdate
from app.services.farm_service import get_user_farm
from app.utils.auth_utils import get_current_user

router = APIRouter()


@router.get("/crops", response_model=list[FarmCropResponse])
async def list_farm_crops(
    farm_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farm = get_user_farm(db, current_user, farm_id)
    db.commit()
    return (
        db.query(FarmCrop)
        .filter(FarmCrop.farm_id == farm.id, FarmCrop.status != "removed")
        .order_by(FarmCrop.added_at.desc())
        .all()
    )


@router.post("/crops", response_model=FarmCropResponse)
async def create_farm_crop(
    crop_data: FarmCropCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farm = get_user_farm(db, current_user, crop_data.farm_id)
    crop = FarmCrop(
        farm_id=farm.id,
        crop_name=crop_data.crop_name,
        variety=crop_data.variety,
        area_acres=crop_data.area_acres,
        planting_date=crop_data.planting_date,
        expected_harvest_date=crop_data.expected_harvest_date,
        added_by=crop_data.added_by,
        status="active",
    )
    db.add(crop)
    db.commit()
    db.refresh(crop)
    return crop


@router.patch("/crops/{crop_id}", response_model=FarmCropResponse)
async def update_farm_crop(
    crop_id: int,
    crop_data: FarmCropUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crop = (
        db.query(FarmCrop)
        .join(FarmCrop.farm)
        .filter(FarmCrop.id == crop_id, FarmCrop.farm.has(user_id=current_user.id))
        .first()
    )
    if not crop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crop not found")

    for field, value in crop_data.model_dump(exclude_unset=True).items():
        setattr(crop, field, value)

    db.commit()
    db.refresh(crop)
    return crop


@router.delete("/crops/{crop_id}")
async def remove_farm_crop(
    crop_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crop = (
        db.query(FarmCrop)
        .join(FarmCrop.farm)
        .filter(FarmCrop.id == crop_id, FarmCrop.farm.has(user_id=current_user.id))
        .first()
    )
    if not crop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crop not found")

    crop.status = "removed"
    db.commit()
    return {"message": "Crop removed successfully"}
