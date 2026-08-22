from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ForumPostCreate(BaseModel):
    region: str
    crop_tag: Optional[str] = None
    title: str
    body: str


class ForumReplyCreate(BaseModel):
    body: str


class ForumReplyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    post_id: int
    user_id: int
    body: str
    hidden: bool
    created_at: datetime


class ForumPostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    region: str
    crop_tag: Optional[str] = None
    title: str
    body: str
    hidden: bool
    created_at: datetime
    replies: list[ForumReplyResponse] = []


class ReportCreate(BaseModel):
    target_type: str
    target_id: int
    reason: str


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    target_type: str
    target_id: int
    reported_by: int
    reason: str
    status: str
    created_at: datetime
