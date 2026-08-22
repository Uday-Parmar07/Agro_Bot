from collections import Counter
from datetime import datetime

from sqlalchemy.orm import Session

from app.database.schemas import DiseasePrediction, FarmCrop, Recommendation, WeatherSnapshot
from app.models.analytics import (
    AnalyticsOverviewResponse,
    CropMixItem,
    DiseaseClassCount,
    RecommendationAdoption,
    SoilScorePoint,
)


def build_analytics_overview(db: Session, farm_id: int) -> AnalyticsOverviewResponse:
    recommendations = (
        db.query(Recommendation)
        .filter(Recommendation.farm_id == farm_id)
        .order_by(Recommendation.generated_at.asc())
        .all()
    )
    disease_predictions = (
        db.query(DiseasePrediction)
        .filter(DiseasePrediction.farm_id == farm_id)
        .all()
    )
    crops = (
        db.query(FarmCrop)
        .filter(FarmCrop.farm_id == farm_id, FarmCrop.status != "removed")
        .all()
    )
    weather_count = (
        db.query(WeatherSnapshot)
        .filter(WeatherSnapshot.farm_id == farm_id)
        .count()
    )

    soil_score_trend = []
    for recommendation in recommendations:
        if recommendation.soil_health_score is None or not recommendation.generated_at:
            continue
        generated_at = recommendation.generated_at
        if isinstance(generated_at, str):
            try:
                generated_at = datetime.fromisoformat(generated_at)
            except ValueError:
                continue
        soil_score_trend.append(
            SoilScorePoint(
                date=generated_at.date(),
                score=float(recommendation.soil_health_score),
            )
        )

    disease_counts = Counter(pred.predicted_class for pred in disease_predictions)
    disease_frequency = [
        DiseaseClassCount(predicted_class=predicted_class, count=count)
        for predicted_class, count in disease_counts.most_common()
    ]

    crop_counts = Counter(crop.crop_name for crop in crops)
    crop_active_counts = Counter(
        crop.crop_name for crop in crops if crop.status == "active"
    )
    crop_mix = [
        CropMixItem(
            crop_name=crop_name,
            count=count,
            active_count=crop_active_counts.get(crop_name, 0),
        )
        for crop_name, count in crop_counts.most_common()
    ]

    latest_recommendation = recommendations[-1] if recommendations else None
    recommended_names = set()
    if latest_recommendation and latest_recommendation.recommended_crops:
        recommended_names = {
            str(crop.get("crop_name", "")).strip().lower()
            for crop in latest_recommendation.recommended_crops
            if crop.get("crop_name")
        }
    adopted_names = {
        str(crop.crop_name).strip().lower()
        for crop in crops
        if str(crop.crop_name).strip().lower() in recommended_names
    }
    recommended_count = len(recommended_names)
    adopted_count = len(adopted_names)
    adoption_rate = round(adopted_count / recommended_count, 2) if recommended_count else 0.0

    return AnalyticsOverviewResponse(
        farm_id=farm_id,
        soil_score_trend=soil_score_trend,
        disease_check_count=len(disease_predictions),
        disease_frequency=disease_frequency,
        crop_mix=crop_mix,
        recommendation_adoption=RecommendationAdoption(
            recommended_count=recommended_count,
            adopted_count=adopted_count,
            adoption_rate=adoption_rate,
        ),
        latest_soil_health_score=(
            float(latest_recommendation.soil_health_score)
            if latest_recommendation and latest_recommendation.soil_health_score is not None
            else None
        ),
        weather_snapshot_count=weather_count,
    )
