from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class MarketplaceListingCreate(BaseModel):
    crop_name: str
    quantity: float
    unit: str
    price: float
    location: Optional[str] = None
    contact_pref: Optional[str] = None


class MarketplaceListingUpdate(BaseModel):
    crop_name: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    price: Optional[float] = None
    location: Optional[str] = None
    contact_pref: Optional[str] = None
    status: Optional[str] = None


class MarketplaceListingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    farmer_id: int
    crop_name: str
    quantity: float
    unit: str
    price: float
    location: Optional[str] = None
    contact_pref: Optional[str] = None
    status: str
    hidden: bool
    created_at: datetime
