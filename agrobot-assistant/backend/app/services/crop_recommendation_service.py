from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.farm_context import DataQualityAssessment, FarmContext
from app.models.recommendation import (
    AIRecommendationResponse,
    CandidateRecommendationStatus,
    CandidateSource,
    CropRecommendation,
    MissingInput,
    ModelPredictionStatus,
    RecommendationCoverage,
    RecommendationStatus,
    ValidationWarning,
)
from app.services.ai_service import ai_service
from app.services.crop_catalog_service import crop_catalog_service
from app.services.crop_prediction_service import crop_prediction_service
from app.services.crop_ranking_service import RANKING_CONFIG, RankedCandidate, crop_ranking_service
from app.services.farm_context_service import farm_context_service
from app.utils.prompt_generator import PROMPT_VERSION


class CropRecommendationService:
    async def generate(
        self,
        db: Session,
        farm_id: int,
        user_id: int,
        user_data: dict[str, Any],
        preferred_language: str,
    ) -> AIRecommendationResponse:
        context, data_quality = await farm_context_service.build(db, farm_id, user_id, user_data)
        model_result = await crop_prediction_service.generate_candidates(context)
        knowledge_candidates = crop_catalog_service.find_knowledge_candidates(context)
        model_candidates = (
            model_result.candidates
            if model_result.status
            in {
                ModelPredictionStatus.SUCCESS,
                ModelPredictionStatus.LOW_CONFIDENCE,
                ModelPredictionStatus.OUT_OF_DISTRIBUTION,
                ModelPredictionStatus.PRELIMINARY_ESTIMATED_INPUT,
                ModelPredictionStatus.PRELIMINARY_MISSING_INPUT,
            }
            else []
        )

        # Rank every eligible candidate before final category selection. This
        # prevents preliminary/rejected entries from occupying one of three
        # recommendation positions merely because they were sliced early.
        ranked = crop_ranking_service.rank(
            model_candidates,
            knowledge_candidates,
            context,
            data_quality,
            model_result.status,
            limit=len(model_candidates) + len(knowledge_candidates),
        )
        recommended = [
            candidate
            for candidate in ranked
            if candidate.recommendation_status == CandidateRecommendationStatus.RECOMMENDED
        ][:3]
        preliminary = [
            candidate
            for candidate in ranked
            if candidate.recommendation_status == CandidateRecommendationStatus.PRELIMINARY
        ][:3]
        displayed = recommended if recommended else preliminary

        coverage = RecommendationCoverage(
            model_supported_crop_count=model_result.model_supported_crop_count,
            knowledge_base_crop_count=len(crop_catalog_service.get_knowledge_profiles()),
            limitation=(
                "The ML model compares the farm only against classes stored in its label encoder. "
                "Additional crops require a complete, sourced crop catalogue profile."
            ),
        )
        global_warnings = self._global_warnings(data_quality, model_result.warnings)
        missing_inputs = self._missing_inputs(context)
        snapshot = {
            "farm_context": context.model_dump(mode="json"),
            "model_feature_values": model_result.feature_values,
            "model_feature_columns": model_result.feature_columns,
            # Detailed ranges and codes stay available for technical review;
            # farmer-facing messages come from `global_warnings`.
            "model_warnings": [warning.model_dump() for warning in model_result.warnings],
            "rainfall_semantics": {
                "questionnaire_annual_rainfall_mm": context.questionnaire_annual_rainfall_mm,
                "seasonal_rainfall_mm": context.seasonal_rainfall_mm,
                "model_compatible_rainfall_mm": context.model_compatible_rainfall_mm,
                "rainfall_unit": context.rainfall_unit,
                "rainfall_period": context.rainfall_period.value,
                "rainfall_compatibility": context.rainfall_compatibility.value,
            },
        }
        common = {
            "user_id": user_id,
            "farm_id": farm_id,
            "coverage": coverage,
            "data_quality": data_quality,
            "global_warnings": global_warnings,
            "missing_inputs": missing_inputs,
            "required_actions": list(dict.fromkeys(item.reason for item in missing_inputs)),
            "model_version": model_result.model_version,
            "crop_catalog_version": crop_catalog_service.catalog_version,
            "prompt_version": PROMPT_VERSION,
            "ranking_rule_version": RANKING_CONFIG.version,
            "weather_source": context.weather_source.value,
            "model_status": model_result.status.value,
            "generated_at": datetime.utcnow(),
            "input_snapshot": snapshot,
        }

        if not displayed:
            return AIRecommendationResponse(
                status=RecommendationStatus.NO_RELIABLE_RECOMMENDATION,
                generation_mode="no_reliable_recommendation",
                explanation_status="not_requested",
                message=(
                    "AgroBot could not find a sufficiently supported crop recommendation "
                    "from the available information."
                ),
                recommended_crops=[],
                preliminary_crops=[],
                general_advice=[
                    "Complete the important farm details shown below before generating another recommendation."
                ],
                disclaimer="No sufficiently reliable crop recommendation is available from the current evidence.",
                **common,
            )

        explanation_result = await ai_service.generate_crop_explanations(
            displayed, context, data_quality, preferred_language
        )
        explanation_by_slug = {
            item.crop_slug: item for item in explanation_result.response.crop_explanations
        }
        crop_payload = [
            self._to_crop(candidate, rank, explanation_by_slug[candidate.crop_slug])
            for rank, candidate in enumerate(displayed, start=1)
        ]

        all_sources = {source for candidate in displayed for source in candidate.candidate_sources}
        if not explanation_result.used_llm:
            generation_mode = "template_fallback"
        elif explanation_result.reason_codes:
            generation_mode = "partial_template"
        elif all_sources == {CandidateSource.XGBOOST, CandidateSource.KNOWLEDGE_BASE}:
            generation_mode = "full_hybrid"
        elif CandidateSource.XGBOOST in all_sources:
            generation_mode = "model_with_explanation"
        else:
            generation_mode = "knowledge_with_explanation"

        normal_crops = crop_payload if recommended else []
        preliminary_crops = crop_payload if not recommended else []
        soil_advice = self._collect(crop_payload, "soil_advice")
        irrigation_advice = self._collect(crop_payload, "irrigation_advice")
        pest_advice = self._collect(crop_payload, "pest_prevention")
        return AIRecommendationResponse(
            status=(RecommendationStatus.SUCCESS if recommended else RecommendationStatus.PRELIMINARY),
            generation_mode=generation_mode,
            explanation_status=explanation_result.public_status,
            internal_llm_reason_codes=[code.value for code in explanation_result.reason_codes],
            message=(
                "Eligible crop recommendations are available."
                if recommended
                else "Only preliminary crop matches are available because important validation is incomplete."
            ),
            recommended_crops=normal_crops,
            preliminary_crops=preliminary_crops,
            general_advice=explanation_result.response.general_advice,
            disclaimer=explanation_result.response.disclaimer,
            soil_improvement_tips=soil_advice,
            irrigation_recommendations=irrigation_advice,
            pest_disease_prevention=pest_advice,
            **common,
        )

    @staticmethod
    def _to_crop(candidate: RankedCandidate, rank: int, explanation) -> CropRecommendation:
        return CropRecommendation(
            crop_slug=candidate.crop_slug,
            crop_name=candidate.crop_name,
            rank=rank,
            candidate_sources=candidate.candidate_sources,
            model_probability=candidate.model_probability,
            model_rank=candidate.model_rank,
            knowledge_score=candidate.knowledge_score,
            overall_suitability_score=candidate.overall_suitability_score,
            suitability_band=candidate.suitability_band,
            recommendation_status=candidate.recommendation_status,
            matched_conditions=candidate.matched_conditions,
            validation_coverage=candidate.validation_coverage,
            validation_coverage_summary=candidate.validation_coverage_summary,
            crop_specific_warnings=candidate.warnings,
            warnings=[],
            source_references=candidate.source_references,
            explanation=explanation,
        )

    @staticmethod
    def _global_warnings(
        data_quality: DataQualityAssessment,
        model_warnings: list[ValidationWarning],
    ) -> list[ValidationWarning]:
        warnings = [
            ValidationWarning(code=warning.code, message=warning.message)
            for warning in data_quality.warnings
        ]
        farmer_messages = {
            "MODEL_INPUT_OUT_OF_RANGE": "One or more supplied values are outside the model's observed training data.",
            "LOW_MODEL_CONFIDENCE": "The model did not find a strong match among its supported crops.",
            "MODEL_UNAVAILABLE": "The crop model is temporarily unavailable.",
            "MODEL_INFERENCE_FAILED": "The crop model could not complete this recommendation.",
            "MISSING_OR_INVALID_FEATURE": "Some information required by the crop model is unavailable.",
            "RAINFALL_PERIOD_INCOMPATIBLE": (
                "The rainfall information provided cannot currently be compared reliably "
                "with the model's training data."
            ),
            "MODEL_RAINFALL_WITHHELD": (
                "The crop model produced preliminary matches without using rainfall because "
                "the available rainfall period is not comparable with its training data."
            ),
        }
        for warning in model_warnings:
            public_code = (
                "RAINFALL_PERIOD_INCOMPATIBLE"
                if warning.code == "MODEL_RAINFALL_WITHHELD"
                else warning.code
            )
            warnings.append(
                ValidationWarning(
                    code=public_code,
                    message=farmer_messages.get(
                        warning.code,
                        "A technical limitation reduced the reliability of the crop-model result.",
                    ),
                )
            )
        return list({warning.code: warning for warning in warnings}.values())

    @staticmethod
    def _missing_inputs(context: FarmContext) -> list[MissingInput]:
        base = f"/questionnaire?refill=1&farm_id={context.farm_id}"
        missing = []
        if context.intended_sowing_date is None:
            missing.append(
                MissingInput(
                    field="intended_sowing_date",
                    importance="high",
                    reason="Needed to evaluate the sowing window.",
                    action_route=f"{base}&section=environment&field=intended_sowing_date",
                    questionnaire_section="environment",
                )
            )
        if context.npk_source.value != "laboratory_test" or context.ph_source.value != "laboratory_test":
            missing.append(
                MissingInput(
                    field="soil_test",
                    importance="high",
                    reason="NPK and pH are currently estimated.",
                    action_route=f"{base}&section=soil-fertility&field=soil_test_done",
                    questionnaire_section="soil-fertility",
                )
            )
        return missing

    @staticmethod
    def _collect(crops: list[CropRecommendation], field_name: str) -> list[str]:
        values = []
        for crop in crops:
            if crop.explanation:
                values.extend(getattr(crop.explanation, field_name))
        return list(dict.fromkeys(values))


crop_recommendation_service = CropRecommendationService()
