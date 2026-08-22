from datetime import date
from typing import List

from pydantic import BaseModel


class SoilScorePoint(BaseModel):
    date: date
    score: float


class DiseaseClassCount(BaseModel):
    predicted_class: str
    count: int


class CropMixItem(BaseModel):
    crop_name: str
    count: int
    active_count: int


class RecommendationAdoption(BaseModel):
    recommended_count: int
    adopted_count: int
    adoption_rate: float


class AnalyticsOverviewResponse(BaseModel):
    farm_id: int
    soil_score_trend: List[SoilScorePoint]
    disease_check_count: int
    disease_frequency: List[DiseaseClassCount]
    crop_mix: List[CropMixItem]
    recommendation_adoption: RecommendationAdoption
    latest_soil_health_score: float | None = None
    weather_snapshot_count: int
