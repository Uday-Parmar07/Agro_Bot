from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime, date

class CropRecommendation(BaseModel):
    crop_name: str
    variety: str
    sowing_season: str
    expected_yield: str
    market_price_range: str
    profitability_score: float

class CalendarEvent(BaseModel):
    date: date
    activity: str
    description: str
    priority: str  # "high", "medium", "low"
    category: str  # "sowing", "fertilizing", "irrigation", "harvesting", "pest_control"

class AIRecommendationResponse(BaseModel):
    user_id: int
    soil_health_score: float
    recommended_crops: List[CropRecommendation]
    farming_calendar: List[CalendarEvent]
    soil_improvement_tips: List[str]
    irrigation_recommendations: List[str]
    fertilizer_recommendations: List[str]
    pest_disease_prevention: List[str]
    generated_at: datetime
    next_review_date: date
