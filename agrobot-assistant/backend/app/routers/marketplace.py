from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.schemas import MarketplaceListing, User
from app.models.marketplace import MarketplaceListingCreate, MarketplaceListingResponse, MarketplaceListingUpdate
from app.utils.auth_utils import get_current_user

router = APIRouter()


@router.post("/listings", response_model=MarketplaceListingResponse)
async def create_listing(
    payload: MarketplaceListingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing = MarketplaceListing(farmer_id=current_user.id, **payload.model_dump())
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


@router.get("/listings", response_model=list[MarketplaceListingResponse])
async def browse_listings(
    crop: str | None = None,
    location: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(MarketplaceListing).filter(
        MarketplaceListing.status == "active",
        MarketplaceListing.hidden == False,  # noqa: E712
    )
    if crop:
        query = query.filter(MarketplaceListing.crop_name.ilike(f"%{crop}%"))
    if location:
        query = query.filter(MarketplaceListing.location.ilike(f"%{location}%"))
    return query.order_by(MarketplaceListing.created_at.desc()).all()


@router.patch("/listings/{listing_id}", response_model=MarketplaceListingResponse)
async def update_listing(
    listing_id: int,
    payload: MarketplaceListingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    if listing.farmer_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(listing, field, value)
    db.commit()
    db.refresh(listing)
    return listing
