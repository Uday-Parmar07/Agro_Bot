from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AdvisorFarmerItem(BaseModel):
    farmer_id: int
    full_name: str
    email: str
    farms_count: int
    latest_soil_score: Optional[float] = None
    disease_checks_30d: int


class AdvisorFarmerSummary(BaseModel):
    farmer_id: int
    full_name: str
    email: str
    latest_soil_score: Optional[float] = None
    disease_checks: int
    disease_flags: list[str]
    weather_snapshots: int
    last_recommendation_at: Optional[datetime] = None
