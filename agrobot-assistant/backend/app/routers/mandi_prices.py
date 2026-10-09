from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.schemas import FarmCrop, User
from app.models.mandi_price import (
    CropMarketNewsResponse,
    MandiCompareResponse,
    MandiCurrentResponse,
    MandiTrendResponse,
)
from app.services.farm_service import get_user_farm
from app.services.crop_news_service import crop_news_service
from app.services.mandi_price_service import mandi_price_service
from app.utils.auth_utils import get_current_user
from app.utils.rate_limit import limiter, user_or_ip

router = APIRouter()


def _active_crops(db: Session, farm_id: int) -> list[FarmCrop]:
    return (
        db.query(FarmCrop)
        .filter(FarmCrop.farm_id == farm_id, FarmCrop.status != "removed")
        .order_by(FarmCrop.added_at.desc())
        .all()
    )


def _select_crop(db: Session, farm_id: int, crop_name: str) -> FarmCrop:
    crop = (
        db.query(FarmCrop)
        .filter(
            FarmCrop.farm_id == farm_id,
            FarmCrop.status != "removed",
            FarmCrop.crop_name.ilike(crop_name),
        )
        .first()
    )
    if not crop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crop '{crop_name}' is not saved for this farm",
        )
    return crop


def _find_crop(db: Session, farm_id: int, crop_name: str) -> FarmCrop | None:
    return (
        db.query(FarmCrop)
        .filter(
            FarmCrop.farm_id == farm_id,
            FarmCrop.status != "removed",
            FarmCrop.crop_name.ilike(crop_name),
        )
        .first()
    )


@router.get("/current", response_model=MandiCurrentResponse)
@limiter.limit("60/minute", key_func=user_or_ip)
async def get_current_mandi_prices(
    request: Request,
    farm_id: int | None = None,
    crop: str = Query(..., min_length=1),
    market: str | None = Query(None, min_length=1),
    state: str | None = Query(None, min_length=1),
    district: str | None = Query(None, min_length=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farm = get_user_farm(db, current_user, farm_id)
    db.commit()
    crops = _active_crops(db, farm.id)

    return await mandi_price_service.get_current_prices(
        db=db,
        farm=farm,
        crop_name=crop,
        available_crops=[saved.crop_name for saved in crops],
        market=market,
        state=state,
        district=district,
    )


@router.get("/compare", response_model=MandiCompareResponse)
@limiter.limit("60/minute", key_func=user_or_ip)
async def compare_mandi_prices(
    request: Request,
    farm_id: int | None = None,
    crop: str = Query(..., min_length=1),
    radius_km: float = Query(250, gt=0, le=2000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farm = get_user_farm(db, current_user, farm_id)
    db.commit()
    crop_record = _find_crop(db, farm.id, crop) or crop
    return await mandi_price_service.compare_mandis(
        db=db,
        farm=farm,
        crop=crop_record,
        radius_km=radius_km,
    )


@router.get("/trend", response_model=MandiTrendResponse)
@limiter.limit("60/minute", key_func=user_or_ip)
async def get_mandi_price_trend(
    request: Request,
    market: str = Query(..., min_length=1),
    crop: str = Query(..., min_length=1),
    days: int = Query(30, ge=7, le=30),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await mandi_price_service.get_price_trend(
        db=db,
        commodity=crop,
        market=market,
        days=days,
    )


@router.get("/news", response_model=CropMarketNewsResponse)
@limiter.limit("10/minute;60/hour", key_func=user_or_ip)
async def get_crop_market_news(
    request: Request,
    crop: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crop_news_service.get_or_fetch_news(db=db, crop=crop)


@router.get("/locations")
async def list_mandi_locations(
    state: str | None = Query(None),
    district: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {
        "locations": mandi_price_service.list_locations(db=db, state=state, district=district)
    }


@router.get("/commodities")
async def search_mandi_commodities(
    q: str = Query("", max_length=80),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {
        "commodities": mandi_price_service.search_commodities(db=db, query=q)
    }
