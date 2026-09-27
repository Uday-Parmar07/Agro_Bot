from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SchemeRecordCreate(BaseModel):
    farm_id: Optional[int] = None
    scheme_name: str
    source_url: Optional[str] = None
    summary: Optional[str] = None
    eligibility_text: Optional[str] = None
    estimated_benefit: Optional[str] = None
    notes: Optional[str] = None


class SchemeRecordUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    applied_at: Optional[datetime] = None


class SchemeRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    farm_id: int
    scheme_name: str
    source_url: Optional[str] = None
    summary: Optional[str] = None
    eligibility_text: Optional[str] = None
    estimated_benefit: Optional[str] = None
    status: str
    applied_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
