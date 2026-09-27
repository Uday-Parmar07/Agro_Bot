import json

from app.models.farm_context import DataQualityAssessment, FarmContext
from app.models.recommendation import CropCandidate
from app.services.crop_catalog_service import CropProfile


PROMPT_VERSION = "crop-explanation-v2"


def generate_crop_explanation_prompt(
    candidates: list[CropCandidate],
    profiles: dict[str, CropProfile],
    context: FarmContext,
    data_quality: DataQualityAssessment,
    preferred_language: str,
) -> str:
    """Build an allow-listed explanation prompt without credentials or raw user records."""
    final_crops = []
    for candidate in candidates:
        profile = profiles[candidate.crop_slug]
        verified_facts = {
            key: value
            for key, value in {
                "allowed_seasons": profile.allowed_seasons or None,
                "sowing_months": profile.sowing_months or None,
                "supported_states": profile.supported_states,
                "supported_districts": profile.supported_districts,
                "supported_soil_types": profile.supported_soil_types or None,
                "ph_range": [profile.min_ph, profile.max_ph]
                if profile.min_ph is not None or profile.max_ph is not None
                else None,
                "temperature_range_c": [profile.min_temperature_c, profile.max_temperature_c]
                if profile.min_temperature_c is not None or profile.max_temperature_c is not None
                else None,
                "rainfall_range_mm": [profile.min_rainfall_mm, profile.max_rainfall_mm]
                if profile.min_rainfall_mm is not None or profile.max_rainfall_mm is not None
                else None,
                "water_requirement": profile.water_requirement,
                "source_name": profile.source_name,
                "source_url": profile.source_url,
            }.items()
            if value is not None
        }
        final_crops.append(
            {
                "crop_slug": candidate.crop_slug,
                "crop_name": candidate.crop_name,
                "candidate_sources": [source.value for source in candidate.candidate_sources],
                "matched_conditions": candidate.matched_conditions,
                "warnings": [warning.model_dump() for warning in candidate.warnings],
                "verified_profile_facts": verified_facts,
            }
        )

    safe_context = {
        "state": context.state,
        "district": context.district,
        "soil_type": context.soil_type,
        "season": context.season,
        "intended_sowing_date": context.intended_sowing_date.isoformat() if context.intended_sowing_date else None,
        "previous_crop": context.previous_crop,
        "irrigation_method": context.irrigation_method,
        "water_availability": context.water_availability,
        "farmer_goal": context.farmer_goal,
    }
    payload = {
        "prompt_version": PROMPT_VERSION,
        "language": "Hindi" if preferred_language == "hi" else "English",
        "allowed_final_crops": final_crops,
        "farm_preferences": safe_context,
        "data_quality": data_quality.model_dump(mode="json"),
    }
    return json.dumps(payload, ensure_ascii=False)
