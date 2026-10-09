import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.schemas import QuestionnaireResponse, Recommendation, User
from app.models.recommendation import (
    AIRecommendationResponse,
    CalendarEvent,
    CropRecommendation,
    RecommendationCoverage,
    RecommendationStatus,
)
from app.services.crop_recommendation_service import crop_recommendation_service
from app.services.crop_ranking_service import RANKING_CONFIG
from app.services.farm_service import get_existing_user_farm
from app.services.government_api_service import generate_government_schemes
from app.utils.auth_utils import get_current_user
from app.utils.rate_limit import limiter, user_or_ip


logger = logging.getLogger(__name__)
router = APIRouter()


def _save_recommendation(
    db: Session,
    user_id: int,
    farm_id: int,
    recommendation: AIRecommendationResponse,
) -> Recommendation:
    payload = recommendation.model_dump(mode="json")
    record = Recommendation(
        user_id=user_id,
        farm_id=farm_id,
        soil_health_score=recommendation.soil_health_score,
        recommended_crops=payload["recommended_crops"],
        farming_calendar=payload["farming_calendar"],
        soil_improvement_tips=payload["soil_improvement_tips"],
        irrigation_recommendations=payload["irrigation_recommendations"],
        fertilizer_recommendations=payload["fertilizer_recommendations"],
        pest_disease_prevention=payload["pest_disease_prevention"],
        next_review_date=(recommendation.next_review_date.isoformat() if recommendation.next_review_date else None),
        status=recommendation.status.value,
        input_snapshot=payload["input_snapshot"],
        data_quality=payload.get("data_quality"),
        model_version=recommendation.model_version,
        model_supported_crop_count=(
            recommendation.coverage.model_supported_crop_count if recommendation.coverage else None
        ),
        crop_catalog_version=recommendation.crop_catalog_version,
        prompt_version=recommendation.prompt_version,
        ranking_rule_version=recommendation.ranking_rule_version,
        weather_source=recommendation.weather_source,
        generation_mode=recommendation.generation_mode,
        model_status=recommendation.model_status,
        explanation_status=recommendation.explanation_status,
        llm_failure_reasons=recommendation.internal_llm_reason_codes,
        final_candidates=payload["recommended_crops"],
        preliminary_candidates=payload["preliminary_crops"],
        global_warnings=payload["global_warnings"],
        missing_inputs=payload["missing_inputs"],
        required_actions=payload["required_actions"],
        recommendation_message=recommendation.message,
        coverage=payload.get("coverage"),
        general_advice=payload.get("general_advice", []),
        disclaimer=recommendation.disclaimer,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def _parse_date(value):
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _db_to_response_model(record: Recommendation, is_stale: bool = False) -> AIRecommendationResponse:
    legacy_global_warnings = {}
    snapshot = record.input_snapshot or {}
    legacy_model_warnings = snapshot.get("model_warnings", []) if isinstance(snapshot, dict) else []
    legacy_rainfall_model_input = (
        isinstance(snapshot, dict)
        and "rainfall_semantics" not in snapshot
        and any(
            "rainfall" in str(warning.get("message", "")).lower()
            for warning in legacy_model_warnings
            if isinstance(warning, dict)
        )
    )

    def normalize_global_warning(warning, index=0):
        data = warning if isinstance(warning, dict) else {
            "code": f"LEGACY_WARNING_{index}",
            "message": str(warning),
        }
        code = str(data.get("code") or f"LEGACY_WARNING_{index}")
        message = str(data.get("message") or "")
        if code in {"ESTIMATED_PH", "ESTIMATED_NPK"} or (
            "npk" in message.lower() and "estimated" in message.lower()
        ):
            return {
                "code": "ESTIMATED_SOIL_VALUES",
                "message": "NPK or pH values were estimated because complete soil-test values were not provided.",
            }
        if "rainfall" in message.lower() or code == "RAINFALL_PERIOD_UNCERTAIN":
            return {
                "code": "RAINFALL_PERIOD_INCOMPATIBLE",
                "message": (
                    "The rainfall information provided cannot currently be compared reliably "
                    "with the model's training data."
                ),
            }
        if code == "MODEL_INPUT_OUT_OF_RANGE":
            return {
                "code": code,
                "message": "One or more supplied values are outside the model's observed training data.",
            }
        if code == "OUT_OF_DISTRIBUTION_MODEL_INPUT":
            return {
                "code": code,
                "message": "Some available farm information is outside the model's observed training data.",
            }
        if code == "SOWING_DATE_UNKNOWN":
            return {
                "code": "SOWING_DATE_MISSING",
                "message": "Add the intended sowing date to check the crop's sowing window.",
            }
        if code == "MISSING_PREVIOUS_CROP":
            return {
                "code": code,
                "message": "Previous crop information is missing, so crop rotation could not be evaluated.",
            }
        return {"code": code, "message": message}

    legacy_global_codes = {
        "ESTIMATED_PH",
        "ESTIMATED_NPK",
        "MOCK_WEATHER",
        "SOWING_DATE_UNKNOWN",
        "OUT_OF_DISTRIBUTION_MODEL_INPUT",
        "LOW_MODEL_CONFIDENCE",
        "RAINFALL_PERIOD_UNCERTAIN",
        "MODEL_INPUT_OUT_OF_RANGE",
        "ESTIMATED_SOIL_VALUES",
        "SOWING_DATE_MISSING",
        "MISSING_PREVIOUS_CROP",
    }

    def parse_crops(raw_items, force_preliminary=False):
        recommended = []
        preliminary = []
        for raw in raw_items or []:
            data = dict(raw)
            # Never revive an explicitly non-positive historical score as a
            # recommendation. Other missing legacy fields remain unknown.
            score = data.get("overall_suitability_score")
            if isinstance(score, (int, float)) and score < RANKING_CONFIG.minimum_preliminary_score:
                continue
            data.setdefault("candidate_sources", [])
            data.setdefault("suitability_band", "insufficient_data")
            data.setdefault("validation_coverage", {})
            data.setdefault("validation_coverage_summary", {})
            crop_warnings = []
            for index, warning in enumerate(data.get("crop_specific_warnings") or data.get("warnings") or []):
                normalized = normalize_global_warning(warning, index)
                if normalized["code"] in legacy_global_codes or normalized["code"] == "RAINFALL_PERIOD_INCOMPATIBLE":
                    legacy_global_warnings[normalized["code"]] = normalized
                elif normalized["code"] not in {
                    "INCOMPLETE_AGRONOMIC_PROFILE",
                    "REGIONAL_COVERAGE_INCOMPLETE",
                    "ROTATION_RULE_UNAVAILABLE",
                    "GOAL_MAPPING_UNAVAILABLE",
                }:
                    crop_warnings.append(normalized)
            data["crop_specific_warnings"] = crop_warnings
            data["warnings"] = []
            sources = set(data.get("candidate_sources") or [])
            if (
                legacy_rainfall_model_input
                and "xgboost" in sources
                and "knowledge_base" not in sources
            ):
                continue
            summary = data.get("validation_coverage_summary") or {}
            verified_checks = int(summary.get("verified_checks") or 0)
            explicit_status = data.get("recommendation_status")
            should_be_preliminary = force_preliminary or (
                isinstance(score, (int, float))
                and (
                    score < RANKING_CONFIG.minimum_recommendation_score
                    or verified_checks < RANKING_CONFIG.minimum_verified_checks_for_recommendation
                    or explicit_status != "recommended"
                )
            )
            if should_be_preliminary:
                data["recommendation_status"] = "preliminary"
                preliminary.append(CropRecommendation(**data))
            else:
                data.setdefault("recommendation_status", "insufficient_support")
                recommended.append(CropRecommendation(**data))
        return recommended, preliminary

    crops, migrated_preliminary = parse_crops(
        record.final_candidates or record.recommended_crops or []
    )
    _, stored_preliminary = parse_crops(record.preliminary_candidates or [], force_preliminary=True)
    preliminary_crops = [*migrated_preliminary, *stored_preliminary]

    calendar = []
    for raw in record.farming_calendar or []:
        data = dict(raw)
        parsed = _parse_date(data.get("date"))
        if parsed:
            data["date"] = parsed
            calendar.append(CalendarEvent(**data))

    coverage_payload = record.coverage
    if not coverage_payload and record.model_supported_crop_count is not None:
        coverage_payload = {
            "model_supported_crop_count": record.model_supported_crop_count,
            "knowledge_base_crop_count": 0,
            "limitation": "Legacy coverage metadata is incomplete.",
        }
    response_status = record.status or RecommendationStatus.SUCCESS.value
    if not crops and preliminary_crops:
        response_status = RecommendationStatus.PRELIMINARY.value
    if not crops and not preliminary_crops and response_status in {
        RecommendationStatus.SUCCESS.value,
        RecommendationStatus.PRELIMINARY.value,
    }:
        response_status = RecommendationStatus.NO_RELIABLE_RECOMMENDATION.value
    response_message = record.recommendation_message
    if response_status == RecommendationStatus.NO_RELIABLE_RECOMMENDATION.value and not response_message:
        response_message = (
            "AgroBot could not find a sufficiently supported crop recommendation "
            "from the available information."
        )
    raw_quality = dict(record.data_quality or {}) if record.data_quality else None
    if raw_quality and raw_quality.get("warnings"):
        normalized_quality_warnings = []
        for index, warning in enumerate(raw_quality["warnings"]):
            normalized = normalize_global_warning(warning, index)
            legacy_global_warnings[normalized["code"]] = normalized
            normalized_quality_warnings.append(normalized)
        raw_quality["warnings"] = normalized_quality_warnings
    stored_global_warnings = {
        warning.get("code") or warning.get("message"): warning
        for warning in (record.global_warnings or [])
        if isinstance(warning, dict)
    }
    stored_global_warnings.update(legacy_global_warnings)
    missing_inputs_payload = list(record.missing_inputs or [])
    warning_codes = set(stored_global_warnings)
    questionnaire_base = f"/questionnaire?refill=1&farm_id={record.farm_id}"
    if not any(item.get("field") == "intended_sowing_date" for item in missing_inputs_payload) and (
        "SOWING_DATE_MISSING" in warning_codes
    ):
        missing_inputs_payload.append(
            {
                "field": "intended_sowing_date",
                "importance": "high",
                "reason": "Needed to evaluate the sowing window.",
                "action_route": f"{questionnaire_base}&section=environment&field=intended_sowing_date",
                "questionnaire_section": "environment",
            }
        )
    if not any(item.get("field") == "soil_test" for item in missing_inputs_payload) and (
        "ESTIMATED_SOIL_VALUES" in warning_codes
    ):
        missing_inputs_payload.append(
            {
                "field": "soil_test",
                "importance": "high",
                "reason": "NPK and pH are currently estimated.",
                "action_route": f"{questionnaire_base}&section=soil-fertility&field=soil_test_done",
                "questionnaire_section": "soil-fertility",
            }
        )
    return AIRecommendationResponse(
        user_id=record.user_id,
        farm_id=record.farm_id,
        status=response_status,
        coverage=RecommendationCoverage(**coverage_payload) if coverage_payload else None,
        data_quality=raw_quality,
        generation_mode=record.generation_mode or "unknown",
        model_version=record.model_version or "unknown",
        crop_catalog_version=record.crop_catalog_version or "unknown",
        prompt_version=record.prompt_version or "unknown",
        ranking_rule_version=record.ranking_rule_version or "unknown",
        weather_source=record.weather_source or "unknown",
        model_status=record.model_status or "unknown",
        explanation_status=record.explanation_status or "unknown",
        is_stale=is_stale,
        message=response_message,
        required_actions=record.required_actions or [item["reason"] for item in missing_inputs_payload],
        missing_inputs=missing_inputs_payload,
        global_warnings=list(stored_global_warnings.values()),
        recommended_crops=crops,
        preliminary_crops=preliminary_crops,
        general_advice=record.general_advice or [],
        disclaimer=record.disclaimer,
        soil_health_score=record.soil_health_score,
        farming_calendar=calendar,
        soil_improvement_tips=record.soil_improvement_tips or [],
        irrigation_recommendations=record.irrigation_recommendations or [],
        fertilizer_recommendations=record.fertilizer_recommendations or [],
        pest_disease_prevention=record.pest_disease_prevention or [],
        generated_at=record.generated_at,
        next_review_date=_parse_date(record.next_review_date),
        input_snapshot=record.input_snapshot or {},
    )


def _questionnaire_user_data(current_user: User, responses: list[QuestionnaireResponse]) -> dict:
    user_data = {
        "user_id": current_user.id,
        "preferred_language": current_user.preferred_language,
    }
    for response in responses:
        user_data[f"set_{response.set_number}"] = response.answers
    return user_data


# Generate and refresh both run the model plus an LLM call, so they share one quota.
GENERATION_LIMIT = "5/minute;30/hour"


async def _generate_recommendations(
    farm_id: int | None,
    current_user: User,
    db: Session,
) -> AIRecommendationResponse:
    if not current_user.onboarding_completed:
        raise HTTPException(status_code=400, detail="Please complete the questionnaire first")
    farm = get_existing_user_farm(db, current_user, farm_id)
    responses = (
        db.query(QuestionnaireResponse)
        .filter(
            QuestionnaireResponse.user_id == current_user.id,
            QuestionnaireResponse.farm_id == farm.id,
        )
        .all()
    )
    present_sets = {response.set_number for response in responses}
    if not set(range(1, 6)).issubset(present_sets):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Incomplete questionnaire data. Found sets {sorted(present_sets)}, need sets 1-5.",
        )
    try:
        recommendation = await crop_recommendation_service.generate(
            db,
            farm.id,
            current_user.id,
            _questionnaire_user_data(current_user, responses),
            current_user.preferred_language,
        )
        _save_recommendation(db, current_user.id, farm.id, recommendation)
        return recommendation
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Safe crop recommendation generation failed")
        raise HTTPException(status_code=500, detail="Recommendation generation failed safely") from exc


@router.post("/generate", response_model=AIRecommendationResponse)
@limiter.shared_limit(GENERATION_LIMIT, scope="recommendation-generation", key_func=user_or_ip)
async def generate_recommendations(
    request: Request,
    farm_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await _generate_recommendations(farm_id, current_user, db)


@router.post("/refresh", response_model=AIRecommendationResponse)
@limiter.shared_limit(GENERATION_LIMIT, scope="recommendation-generation", key_func=user_or_ip)
async def refresh_recommendations(
    request: Request,
    farm_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await _generate_recommendations(farm_id, current_user, db)


@router.get("/latest", response_model=AIRecommendationResponse)
async def get_latest_recommendations(
    farm_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farm = get_existing_user_farm(db, current_user, farm_id)
    latest = (
        db.query(Recommendation)
        .filter(Recommendation.user_id == current_user.id, Recommendation.farm_id == farm.id)
        .order_by(Recommendation.generated_at.desc())
        .first()
    )
    if not latest:
        raise HTTPException(status_code=404, detail="No recommendations found. Generate recommendations first.")
    responses = (
        db.query(QuestionnaireResponse)
        .filter(
            QuestionnaireResponse.user_id == current_user.id,
            QuestionnaireResponse.farm_id == farm.id,
        )
        .all()
    )
    latest_questionnaire_update = max((item.updated_at for item in responses), default=None)
    is_stale = bool(latest_questionnaire_update and latest.generated_at < latest_questionnaire_update)
    return _db_to_response_model(latest, is_stale=is_stale)


def _build_user_profile_from_responses(responses):
    sets = {response.set_number: response.answers for response in responses}
    environment, irrigation, soil = sets.get(4, {}), sets.get(3, {}), sets.get(1, {})
    acreage = None
    if environment.get("total_area"):
        acreage = f"{environment['total_area']} {environment.get('area_unit') or 'acre'}"
    return {
        "location": environment.get("state") or environment.get("district") or "India",
        "state": environment.get("state"),
        "district": environment.get("district"),
        "acreage": acreage,
        "irrigation": irrigation.get("irrigation_type"),
        "soil_type": soil.get("soil_texture"),
        "average_rainfall": environment.get("average_rainfall"),
        "average_temperature": environment.get("average_temperature"),
    }


@router.get("/government-schemes")
@limiter.limit("5/minute;30/hour", key_func=user_or_ip)
async def get_government_schemes(
    request: Request,
    farm_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farm = get_existing_user_farm(db, current_user, farm_id)
    responses = (
        db.query(QuestionnaireResponse)
        .filter(
            QuestionnaireResponse.user_id == current_user.id,
            QuestionnaireResponse.farm_id == farm.id,
        )
        .all()
    )
    if not responses:
        raise HTTPException(status_code=400, detail="No questionnaire data found.")
    profile = _build_user_profile_from_responses(responses)
    profile["preferred_language"] = current_user.preferred_language
    return generate_government_schemes(profile)


@router.get("/history")
async def get_recommendation_history(
    farm_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farm = get_existing_user_farm(db, current_user, farm_id)
    records = (
        db.query(Recommendation)
        .filter(Recommendation.user_id == current_user.id, Recommendation.farm_id == farm.id)
        .order_by(Recommendation.generated_at.desc())
        .all()
    )
    return [
        {
            "id": record.id,
            "status": record.status or "unknown",
            "generation_mode": record.generation_mode or "unknown",
            "model_version": record.model_version or "unknown",
            "soil_health_score": record.soil_health_score,
            "generated_at": record.generated_at,
            "next_review_date": record.next_review_date,
            "crops_count": len(
                (record.final_candidates or record.recommended_crops or [])
                + (record.preliminary_candidates or [])
            ),
            "calendar_events_count": len(record.farming_calendar or []),
        }
        for record in records
    ]
