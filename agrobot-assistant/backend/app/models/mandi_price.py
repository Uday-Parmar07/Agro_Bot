from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class MandiPricePoint(BaseModel):
    market_name: str
    state: Optional[str] = None
    district: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    modal_price: Optional[float] = None
    arrival_qty: Optional[float] = None
    price_date: Optional[date] = None
    fetched_at: Optional[datetime] = None
    distance_km: Optional[float] = None
    data_status: str = "available"


class MandiPriceSummary(BaseModel):
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    modal_price: Optional[float] = None
    market_count: int = 0
    price_date: Optional[date] = None
    data_status: str = "no_data"


class MandiCurrentResponse(BaseModel):
    farm_id: int
    crop: str
    available_crops: list[str]
    nearby: list[MandiPricePoint]
    state_summary: MandiPriceSummary
    india_summary: MandiPriceSummary
    primary_market: Optional[str] = None


class MandiTripCandidate(BaseModel):
    market_name: str
    state: Optional[str] = None
    district: Optional[str] = None
    distance_km: Optional[float] = None
    modal_price: Optional[float] = None
    baseline_price: Optional[float] = None
    expected_quantity_quintals: float
    gross_gain: float
    transport_cost: float
    net_gain: float
    price_date: Optional[date] = None
    worth_trip: bool


class MandiCompareResponse(BaseModel):
    farm_id: int
    crop: str
    radius_km: float
    baseline_market: Optional[MandiPricePoint] = None
    recommendations: list[MandiTripCandidate]
    best_candidate: Optional[MandiTripCandidate] = None
    threshold: float
    transport_cost_per_km: float


class MandiTrendPoint(BaseModel):
    date: date
    modal_price: Optional[float] = None
    data_status: str = "available"


class MandiTrendResponse(BaseModel):
    market: str
    crop: str
    days: int
    points: list[MandiTrendPoint]
    direction: str
    change_abs: Optional[float] = None
    change_pct: Optional[float] = None


class MandiSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    commodity: str
    market_name: str
    state: Optional[str] = None
    district: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    modal_price: Optional[float] = None
    arrival_qty: Optional[float] = None
    price_date: date
    fetched_at: Optional[datetime] = None


class CropMarketNewsItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    crop: str
    headline: str
    summary: str
    source_url: Optional[str] = None
    published_or_found_at: Optional[datetime] = None
    cached_for_date: date


class CropMarketNewsResponse(BaseModel):
    crop: str
    cached_for_date: date
    insights: list[CropMarketNewsItem]
    data_status: str = "available"
