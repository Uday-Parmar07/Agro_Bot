from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class FarmCropCreate(BaseModel):
    farm_id: Optional[int] = None
    crop_name: str
    variety: Optional[str] = None
    area_acres: Optional[float] = None
    planting_date: Optional[date] = None
    expected_harvest_date: Optional[date] = None
    added_by: str = "user"


class FarmCropUpdate(BaseModel):
    crop_name: Optional[str] = None
    variety: Optional[str] = None
    area_acres: Optional[float] = None
    planting_date: Optional[date] = None
    expected_harvest_date: Optional[date] = None
    status: Optional[str] = None


class FarmCropResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    farm_id: int
    crop_name: str
    variety: Optional[str] = None
    area_acres: Optional[float] = None
    planting_date: Optional[date] = None
    expected_harvest_date: Optional[date] = None
    added_by: str
    status: str
    added_at: datetime
