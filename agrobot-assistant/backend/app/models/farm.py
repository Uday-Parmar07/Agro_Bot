from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class FarmCreate(BaseModel):
    name: str
    location: Optional[str] = None
    area_acres: Optional[float] = None


class FarmResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    location: Optional[str] = None
    area_acres: Optional[float] = None
    created_at: datetime
