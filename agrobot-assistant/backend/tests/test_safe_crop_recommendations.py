import json
import tempfile
import unittest
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.schemas import Base, Farm, Recommendation, User
from app.models.farm_context import (
    DataQualityAssessment,
    DataQualityLevel,
    DataSource,
    FarmContext,
    InputWarning,
    RainfallCompatibility,
    RainfallPeriod,
)
from app.models.recommendation import (
    AIRecommendationResponse,
    CandidateRecommendationStatus,
    CandidateSource,
    CropCandidate,
    CropExplanation,
    CropModelResult,
    CropRecommendation,
    ExplanationFailureCode,
    LLMExplanationResponse,
    ModelPredictionStatus,
    RecommendationStatus,
    ValidationStatus,
    ValidationWarning,
)
from app.routers.recommendations import _db_to_response_model, _save_recommendation
from app.services.ai_service import AIService, ExplanationGenerationResult
from app.services.crop_catalog_service import (
    CropCatalogService,
    CropProfile,
    canonical_crop_slug,
    crop_catalog_service,
)
from app.services.crop_prediction_service import crop_prediction_service
from app.services.crop_ranking_service import crop_ranking_service
from app.services.crop_recommendation_service import crop_recommendation_service
from app.services.crop_validation_service import crop_validation_service
from app.services.farm_context_service import farm_context_service
from app.services.farm_service import get_user_farm


def context(**updates):
    values = {
        "farm_id": 1,
        "user_id": 1,
        "state": "Maharashtra",
        "district": "Pune",
        "soil_type": "loamy",
        "season": "rabi",
        "intended_sowing_date": date(2026, 11, 1),
        "irrigation_method": "drip",
        "water_availability": "assured",
        "nitrogen": 50.0,
        "phosphorus": 40.0,
        "potassium": 35.0,
        "ph": 6.8,
        "temperature": 27.0,
        "humidity": 60.0,
        "rainfall_value": 100.0,
        "rainfall_period": RainfallPeriod.TRAINING_DATASET_UNSPECIFIED,
        "rainfall_compatibility": RainfallCompatibility.COMPATIBLE,
        "model_compatible_rainfall_mm": 100.0,
        "npk_source": DataSource.LABORATORY_TEST,
        "ph_source": DataSource.LABORATORY_TEST,
        "temperature_source": DataSource.FARMER_PROVIDED,
        "humidity_source": DataSource.WEATHER_API,
        "rainfall_source": DataSource.FARMER_PROVIDED,
        "weather_source": DataSource.WEATHER_API,
    }
    values.update(updates)
    return FarmContext(**values)


def profile(slug="verifiedcrop", **updates):
    values = {
        "crop_slug": slug,
        "display_name": slug.title(),
        "is_active": True,
        "is_model_supported": False,
        "knowledge_profile_complete": True,
        "allowed_seasons": ["rabi"],
        "sowing_months": [11],
        "supported_states": ["Maharashtra"],
        "supported_districts": None,
        "supported_soil_types": ["loamy"],
        "min_ph": 6.0,
        "max_ph": 7.5,
        "source_name": "Test verified source",
        "source_url": "https://example.test/crop",
        "profile_version": "test-v1",
    }
    values.update(updates)
    return CropProfile(**values)


@contextmanager
def installed_profile(item: CropProfile):
    old = crop_catalog_service._profiles.get(item.crop_slug)
    crop_catalog_service._profiles[item.crop_slug] = item
    try:
        yield
    finally:
        if old is None:
            crop_catalog_service._profiles.pop(item.crop_slug, None)
        else:
            crop_catalog_service._profiles[item.crop_slug] = old


class SafeCropRecommendationTests(unittest.IsolatedAsyncioTestCase):
    async def test_xgboost_candidates_are_actual_model_classes(self):
        result = await crop_prediction_service.generate_candidates(context(), top_k=22)
        actual = {canonical_crop_slug(item) for item in crop_prediction_service.get_model_classes()}
        self.assertTrue({item.crop_slug for item in result.candidates}.issubset(actual))

    def test_knowledge_candidates_only_use_active_catalogue(self):
        payload = {
            "catalog_version": "test",
            "profile_defaults": {"profile_version": "test"},
            "profiles": [
                profile("active").model_dump(mode="json"),
                profile("inactive", is_active=False).model_dump(mode="json"),
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            service = CropCatalogService(path)
            candidates = service.find_knowledge_candidates(context())
        self.assertEqual([item.crop_slug for item in candidates], ["active"])

    def test_unauthorized_llm_crop_is_rejected(self):
        response = LLMExplanationResponse(
            crop_explanations=[CropExplanation(crop_slug="invented", summary="Unsupported")],
            disclaimer="Test",
        )
        with self.assertRaises(ValueError) as raised:
            AIService()._normalize_response(response, response, ["rice"])
        self.assertEqual(raised.exception.code, ExplanationFailureCode.LLM_UNAUTHORIZED_CROP)

    def test_knowledge_only_probability_is_null(self):
        item = profile()
        with installed_profile(item):
            candidate = crop_catalog_service.find_knowledge_candidates(context())[0]
        self.assertIsNone(candidate.model_probability)

    def test_both_lanes_merge_without_fake_probability(self):
        model = CropCandidate(crop_slug="rice", crop_name="Rice", candidate_sources=[CandidateSource.XGBOOST], model_probability=.7)
        knowledge = CropCandidate(crop_slug="rice", crop_name="Rice", candidate_sources=[CandidateSource.KNOWLEDGE_BASE], knowledge_score=.8)
        merged = crop_ranking_service.merge_candidates([[model], [knowledge]])[0]
        self.assertEqual(set(merged.candidate_sources), {CandidateSource.XGBOOST, CandidateSource.KNOWLEDGE_BASE})
        self.assertEqual(merged.model_probability, .7)
        self.assertEqual(merged.knowledge_score, .8)

    def test_duplicate_casing_is_canonicalized(self):
        one = CropCandidate(crop_slug="Rice", crop_name="Rice", candidate_sources=[CandidateSource.XGBOOST], model_probability=.5)
        two = CropCandidate(crop_slug=" rice ", crop_name="RICE", candidate_sources=[CandidateSource.KNOWLEDGE_BASE], knowledge_score=.5)
        self.assertEqual(len(crop_ranking_service.merge_candidates([[one], [two]])), 1)

    def test_hard_season_incompatibility_rejects(self):
        item = profile(allowed_seasons=["kharif"])
        candidate = CropCandidate(crop_slug=item.crop_slug, crop_name=item.display_name, candidate_sources=[CandidateSource.KNOWLEDGE_BASE], knowledge_score=.8)
        with installed_profile(item):
            result = crop_validation_service.validate(candidate, context(), ModelPredictionStatus.MODEL_UNAVAILABLE)
        self.assertEqual(result.status, ValidationStatus.REJECTED)
        self.assertIn("SEASON_INCOMPATIBLE", {issue.code for issue in result.hard_failures})

    def test_estimated_ph_warns_instead_of_hard_rejecting(self):
        item = profile(min_ph=5.0, max_ph=6.0)
        candidate = CropCandidate(crop_slug=item.crop_slug, crop_name=item.display_name, candidate_sources=[CandidateSource.KNOWLEDGE_BASE], knowledge_score=.8)
        with installed_profile(item):
            result = crop_validation_service.validate(
                candidate,
                context(ph=7.0, ph_source=DataSource.QUESTIONNAIRE_ESTIMATE),
                ModelPredictionStatus.MODEL_UNAVAILABLE,
            )
        self.assertEqual(result.status, ValidationStatus.ELIGIBLE)
        self.assertIn("ESTIMATED_PH_OUTSIDE_RANGE", {issue.code for issue in result.warnings})

    def test_missing_soil_test_is_low_quality(self):
        assessment = farm_context_service.assess_data_quality(
            context(npk_source=DataSource.QUESTIONNAIRE_ESTIMATE, ph_source=DataSource.QUESTIONNAIRE_ESTIMATE)
        )
        self.assertEqual(assessment.level, DataQualityLevel.LOW)
        self.assertIn("N", assessment.estimated_features)

    def test_mock_weather_is_labelled_and_reduces_quality(self):
        assessment = farm_context_service.assess_data_quality(
            context(weather_source=DataSource.MOCK_FALLBACK, humidity_source=DataSource.MOCK_FALLBACK)
        )
        self.assertEqual(assessment.level, DataQualityLevel.LOW)
        self.assertIn("MOCK_WEATHER", {warning.code for warning in assessment.warnings})

    async def test_llm_failure_preserves_deterministic_recommendations(self):
        candidate = CropCandidate(
            crop_slug="rice",
            crop_name="Rice",
            candidate_sources=[CandidateSource.XGBOOST],
            model_probability=.7,
        )
        model_result = CropModelResult(
            status=ModelPredictionStatus.SUCCESS,
            candidates=[candidate],
            model_version="test-model",
            model_supported_crop_count=22,
            model_classes=["rice"],
            feature_columns=list(context().model_features()),
            feature_values=context().model_features(),
        )
        templates = LLMExplanationResponse(
            crop_explanations=[CropExplanation(crop_slug="rice", summary="Safe template")],
            disclaimer="Template disclaimer",
        )
        explanation_result = ExplanationGenerationResult(templates, False, [ExplanationFailureCode.LLM_REQUEST_FAILED])
        item = profile("rice", is_model_supported=True)
        with installed_profile(item), \
             patch.object(farm_context_service, "build", AsyncMock(return_value=(context(), DataQualityAssessment(level="medium")))), \
             patch.object(crop_prediction_service, "generate_candidates", AsyncMock(return_value=model_result)), \
             patch.object(AIService, "generate_crop_explanations", AsyncMock(return_value=explanation_result)):
            response = await crop_recommendation_service.generate(Mock(), 1, 1, {}, "en")
        self.assertEqual(response.generation_mode, "template_fallback")
        self.assertEqual([item.crop_slug for item in response.recommended_crops], ["rice"])
        self.assertEqual(response.status, RecommendationStatus.SUCCESS)
        self.assertGreater(response.recommended_crops[0].overall_suitability_score, 0)
        self.assertEqual(response.global_warnings, [])
        self.assertIn("LLM_REQUEST_FAILED", response.internal_llm_reason_codes)
        self.assertNotIn("internal_llm_reason_codes", response.model_dump(mode="json"))

    async def test_xgboost_failure_can_use_eligible_knowledge_candidate(self):
        item = profile()
        model_result = CropModelResult(
            status=ModelPredictionStatus.MODEL_UNAVAILABLE,
            model_version="unavailable",
            model_supported_crop_count=0,
        )
        explanation = LLMExplanationResponse(
            crop_explanations=[CropExplanation(crop_slug=item.crop_slug, summary="Verified profile match")],
            disclaimer="Test",
        )
        explanation_result = ExplanationGenerationResult(explanation, True)
        with installed_profile(item), \
             patch.object(farm_context_service, "build", AsyncMock(return_value=(context(), DataQualityAssessment(level="medium")))), \
             patch.object(crop_prediction_service, "generate_candidates", AsyncMock(return_value=model_result)), \
             patch.object(AIService, "generate_crop_explanations", AsyncMock(return_value=explanation_result)):
            response = await crop_recommendation_service.generate(Mock(), 1, 1, {}, "en")
        self.assertEqual(response.recommended_crops[0].crop_slug, item.crop_slug)
        self.assertIsNone(response.recommended_crops[0].model_probability)
        self.assertEqual(response.generation_mode, "knowledge_with_explanation")

    async def test_both_sources_failing_returns_no_reliable_recommendation(self):
        model_result = CropModelResult(status=ModelPredictionStatus.MODEL_UNAVAILABLE)
        with patch.object(farm_context_service, "build", AsyncMock(return_value=(context(), DataQualityAssessment(level="low")))), \
             patch.object(crop_prediction_service, "generate_candidates", AsyncMock(return_value=model_result)):
            response = await crop_recommendation_service.generate(Mock(), 1, 1, {}, "en")
        self.assertEqual(response.status, RecommendationStatus.NO_RELIABLE_RECOMMENDATION)
        self.assertEqual(response.recommended_crops, [])

    def test_repeated_storage_remains_farm_scoped(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()
        user = User(email="one@example.test", hashed_password="x", full_name="One")
        session.add(user)
        session.flush()
        farm = Farm(user_id=user.id, name="Farm One")
        session.add(farm)
        session.commit()
        response = AIRecommendationResponse(
            user_id=user.id,
            farm_id=farm.id,
            generated_at=datetime.utcnow(),
            internal_llm_reason_codes=["LLM_TIMEOUT"],
        )
        _save_recommendation(session, user.id, farm.id, response)
        _save_recommendation(session, user.id, farm.id, response)
        records = session.query(Recommendation).all()
        self.assertEqual(len(records), 2)
        self.assertEqual({record.farm_id for record in records}, {farm.id})
        self.assertTrue(all(record.llm_failure_reasons == ["LLM_TIMEOUT"] for record in records))

    def test_user_cannot_resolve_another_users_farm(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()
        first = User(email="first@example.test", hashed_password="x", full_name="First")
        second = User(email="second@example.test", hashed_password="x", full_name="Second")
        session.add_all([first, second])
        session.flush()
        foreign_farm = Farm(user_id=second.id, name="Foreign")
        session.add(foreign_farm)
        session.commit()
        with self.assertRaises(Exception):
            get_user_farm(session, first, foreign_farm.id)

    def test_legacy_recommendation_is_readable(self):
        record = Recommendation(
            user_id=1,
            farm_id=1,
            recommended_crops=[{
                "crop_name": "Rice", "variety": "Legacy", "sowing_season": "Kharif",
                "expected_yield": "legacy", "market_price_range": "legacy", "profitability_score": 7.0,
            }],
            farming_calendar=[],
            generated_at=datetime.utcnow(),
        )
        response = _db_to_response_model(record)
        self.assertEqual(response.recommended_crops[0].suitability_band.value, "insufficient_data")
        self.assertEqual(response.recommended_crops[0].candidate_sources, [])

    def test_stored_zero_scores_are_removed_and_low_scores_become_preliminary(self):
        record = Recommendation(
            user_id=1,
            farm_id=1,
            status="success",
            final_candidates=[
                {"crop_slug": "rice", "crop_name": "Rice", "overall_suitability_score": 0},
                {"crop_slug": "papaya", "crop_name": "Papaya", "overall_suitability_score": 44},
            ],
            farming_calendar=[],
            generated_at=datetime.utcnow(),
        )
        response = _db_to_response_model(record)
        self.assertEqual(response.status, RecommendationStatus.PRELIMINARY)
        self.assertEqual(response.recommended_crops, [])
        self.assertEqual([crop.crop_slug for crop in response.preliminary_crops], ["papaya"])

    def test_legacy_model_candidate_using_incompatible_rainfall_is_not_revived(self):
        record = Recommendation(
            user_id=1,
            farm_id=1,
            status="success",
            model_status="out_of_distribution",
            input_snapshot={
                "model_warnings": [
                    {"code": "MODEL_INPUT_OUT_OF_RANGE", "message": "rainfall is outside the observed range"}
                ]
            },
            final_candidates=[
                {
                    "crop_slug": "papaya",
                    "crop_name": "Papaya",
                    "candidate_sources": ["xgboost"],
                    "overall_suitability_score": 44,
                }
            ],
            farming_calendar=[],
            generated_at=datetime.utcnow(),
        )
        response = _db_to_response_model(record)
        self.assertEqual(response.status, RecommendationStatus.NO_RELIABLE_RECOMMENDATION)
        self.assertEqual(response.recommended_crops, [])
        self.assertEqual(response.preliminary_crops, [])

    def test_suitability_and_profitability_are_separate(self):
        crop = CropRecommendation(crop_name="Rice", overall_suitability_score=70, profitability_score=None)
        self.assertEqual(crop.overall_suitability_score, 70)
        self.assertIsNone(crop.profitability_score)

    def test_supported_crop_count_is_derived_from_encoder(self):
        classes = crop_prediction_service.get_model_classes()
        self.assertEqual(len(classes), 22)
        self.assertEqual(len(classes), len(set(classes)))

    async def test_out_of_range_input_has_distribution_status(self):
        result = await crop_prediction_service.generate_candidates(
            context(rainfall_value=9000.0, model_compatible_rainfall_mm=9000.0), top_k=3
        )
        self.assertEqual(result.status, ModelPredictionStatus.OUT_OF_DISTRIBUTION)
        self.assertIn("MODEL_INPUT_OUT_OF_RANGE", {warning.code for warning in result.warnings})

    async def test_missing_weather_feature_is_invalid_input_not_a_hidden_default(self):
        result = await crop_prediction_service.generate_candidates(
            context(humidity=None, humidity_source=DataSource.UNKNOWN), top_k=3
        )
        self.assertEqual(result.status, ModelPredictionStatus.INVALID_INPUT)
        self.assertEqual(result.candidates, [])

    def test_knowledge_candidate_cannot_carry_fake_model_probability(self):
        item = profile()
        candidate = CropCandidate(
            crop_slug=item.crop_slug,
            crop_name=item.display_name,
            candidate_sources=[CandidateSource.KNOWLEDGE_BASE],
            model_probability=.9,
            knowledge_score=.8,
        )
        with installed_profile(item):
            validation = crop_validation_service.validate(candidate, context(), ModelPredictionStatus.MODEL_UNAVAILABLE)
        self.assertIn("UNSUPPORTED_MODEL_PROBABILITY", {issue.code for issue in validation.hard_failures})

    def test_incomplete_knowledge_profile_cannot_be_final(self):
        item = profile(knowledge_profile_complete=False)
        candidate = CropCandidate(crop_slug=item.crop_slug, crop_name=item.display_name, candidate_sources=[CandidateSource.KNOWLEDGE_BASE], knowledge_score=.9)
        with installed_profile(item):
            validation = crop_validation_service.validate(candidate, context(), ModelPredictionStatus.MODEL_UNAVAILABLE)
        self.assertEqual(validation.status, ValidationStatus.REJECTED)

    async def test_annual_rainfall_is_not_compared_to_training_range(self):
        annual_context = context(
            rainfall_value=9000.0,
            questionnaire_annual_rainfall_mm=9000.0,
            rainfall_period=RainfallPeriod.ANNUAL,
            rainfall_compatibility=RainfallCompatibility.INCOMPATIBLE_PERIOD,
            model_compatible_rainfall_mm=None,
        )
        result = await crop_prediction_service.generate_candidates(annual_context, top_k=3)
        self.assertEqual(result.status, ModelPredictionStatus.PRELIMINARY_MISSING_INPUT)
        self.assertNotIn("MODEL_INPUT_OUT_OF_RANGE", {warning.code for warning in result.warnings})
        self.assertIn("MODEL_RAINFALL_WITHHELD", {warning.code for warning in result.warnings})
        self.assertIsNone(result.feature_values["rainfall"])
        self.assertTrue(result.candidates)

    async def test_annual_rainfall_pipeline_returns_only_preliminary_model_matches(self):
        annual_context = context(
            rainfall_value=700.0,
            questionnaire_annual_rainfall_mm=700.0,
            rainfall_period=RainfallPeriod.ANNUAL,
            rainfall_compatibility=RainfallCompatibility.INCOMPATIBLE_PERIOD,
            model_compatible_rainfall_mm=None,
        )
        quality = farm_context_service.assess_data_quality(annual_context)
        with patch.object(
            farm_context_service,
            "build",
            AsyncMock(return_value=(annual_context, quality)),
        ):
            response = await crop_recommendation_service.generate(Mock(), 1, 1, {}, "en")
        self.assertEqual(response.model_status, "preliminary_missing_input")
        self.assertEqual(response.status, RecommendationStatus.PRELIMINARY)
        self.assertEqual(response.recommended_crops, [])
        self.assertGreaterEqual(len(response.preliminary_crops), 1)
        self.assertTrue(all(item.recommendation_status == "preliminary" for item in response.preliminary_crops))

    async def test_missing_rainfall_semantics_has_explicit_status(self):
        result = await crop_prediction_service.generate_candidates(
            context(
                rainfall_value=None,
                rainfall_period=RainfallPeriod.UNKNOWN,
                rainfall_compatibility=RainfallCompatibility.UNKNOWN,
                model_compatible_rainfall_mm=None,
            ),
            top_k=3,
        )
        self.assertEqual(result.status, ModelPredictionStatus.PRELIMINARY_MISSING_INPUT)
        self.assertIn("MODEL_RAINFALL_WITHHELD", {warning.code for warning in result.warnings})

    async def test_missing_rainfall_preliminary_mode_can_be_disabled(self):
        with patch.dict(
            "os.environ",
            {"ENABLE_PRELIMINARY_MODEL_WITH_MISSING_RAINFALL": "false"},
        ):
            result = await crop_prediction_service.generate_candidates(
                context(
                    rainfall_value=700.0,
                    rainfall_period=RainfallPeriod.ANNUAL,
                    rainfall_compatibility=RainfallCompatibility.INCOMPATIBLE_PERIOD,
                    model_compatible_rainfall_mm=None,
                ),
                top_k=3,
            )
        self.assertEqual(result.status, ModelPredictionStatus.INSUFFICIENT_COMPATIBLE_INPUT)
        self.assertEqual(result.candidates, [])

    def test_zero_and_negative_signal_candidates_are_excluded(self):
        for probability in (0.0, -0.2):
            candidate = CropCandidate(
                crop_slug="rice",
                crop_name="Rice",
                candidate_sources=[CandidateSource.XGBOOST],
                model_probability=probability,
            )
            ranked = crop_ranking_service.rank(
                [candidate], [], context(), DataQualityAssessment(level="medium"), ModelPredictionStatus.SUCCESS
            )
            self.assertEqual(ranked, [])

    def test_hard_failed_candidate_is_excluded_from_ranking(self):
        item = profile("blocked", allowed_seasons=["kharif"])
        candidate = CropCandidate(
            crop_slug=item.crop_slug,
            crop_name=item.display_name,
            candidate_sources=[CandidateSource.KNOWLEDGE_BASE],
            knowledge_score=.9,
        )
        with installed_profile(item):
            ranked = crop_ranking_service.rank(
                [], [candidate], context(), DataQualityAssessment(level="medium"), ModelPredictionStatus.MODEL_UNAVAILABLE
            )
        self.assertEqual(ranked, [])

    def test_one_or_two_candidates_are_not_padded(self):
        candidates = [
            CropCandidate(
                crop_slug=slug,
                crop_name=slug.title(),
                candidate_sources=[CandidateSource.XGBOOST],
                model_probability=probability,
            )
            for slug, probability in (("rice", .8), ("maize", .7))
        ]
        one = crop_ranking_service.rank(
            candidates[:1], [], context(), DataQualityAssessment(level="medium"), ModelPredictionStatus.SUCCESS
        )
        two = crop_ranking_service.rank(
            candidates, [], context(), DataQualityAssessment(level="medium"), ModelPredictionStatus.SUCCESS
        )
        self.assertEqual(len(one), 1)
        self.assertEqual(len(two), 2)

    def test_missing_catalogue_season_is_not_available(self):
        candidate = CropCandidate(
            crop_slug="rice",
            crop_name="Rice",
            candidate_sources=[CandidateSource.XGBOOST],
            model_probability=.8,
        )
        validation = crop_validation_service.validate(candidate, context(), ModelPredictionStatus.SUCCESS)
        self.assertEqual(validation.validation_coverage.season.value, "not_available")
        self.assertGreaterEqual(validation.validation_coverage_summary.unavailable_checks, 1)
        self.assertIn(
            "NO_VERIFIED_AGRONOMIC_CHECKS",
            {warning.code for warning in validation.warnings},
        )

    def test_missing_sowing_date_is_structured_action(self):
        missing = crop_recommendation_service._missing_inputs(context(intended_sowing_date=None))
        item = next(entry for entry in missing if entry.field == "intended_sowing_date")
        self.assertEqual(item.questionnaire_section, "environment")
        self.assertIn("farm_id=1", item.action_route)
        self.assertIn("field=intended_sowing_date", item.action_route)

    async def test_global_warnings_are_not_copied_into_crop(self):
        candidate = CropCandidate(
            crop_slug="rice",
            crop_name="Rice",
            candidate_sources=[CandidateSource.XGBOOST],
            model_probability=.8,
        )
        model_result = CropModelResult(
            status=ModelPredictionStatus.SUCCESS,
            candidates=[candidate],
            model_version="test",
            model_supported_crop_count=22,
        )
        quality = DataQualityAssessment(
            level="medium",
            warnings=[InputWarning(code="GLOBAL_TEST", message="Global only")],
        )
        explanation = LLMExplanationResponse(
            crop_explanations=[CropExplanation(crop_slug="rice", summary="Safe")],
            disclaimer="Test",
        )
        explanation_result = ExplanationGenerationResult(explanation, True)
        with patch.object(farm_context_service, "build", AsyncMock(return_value=(context(), quality))), \
             patch.object(crop_prediction_service, "generate_candidates", AsyncMock(return_value=model_result)), \
             patch.object(AIService, "generate_crop_explanations", AsyncMock(return_value=explanation_result)):
            response = await crop_recommendation_service.generate(Mock(), 1, 1, {}, "en")
        self.assertIn("GLOBAL_TEST", {warning.code for warning in response.global_warnings})
        displayed = response.preliminary_crops or response.recommended_crops
        self.assertNotIn("GLOBAL_TEST", {warning.code for warning in displayed[0].crop_specific_warnings})
        self.assertEqual(displayed[0].warnings, [])

    def test_reordered_llm_output_is_accepted_and_normalized(self):
        service = AIService()
        candidates = [
            CropCandidate(crop_slug="rice", crop_name="Rice", candidate_sources=[CandidateSource.XGBOOST], model_probability=.7),
            CropCandidate(crop_slug="maize", crop_name="Maize", candidate_sources=[CandidateSource.XGBOOST], model_probability=.6),
        ]
        templates = service._template_response(candidates, DataQualityAssessment(level="medium"), "en")
        response = LLMExplanationResponse(
            crop_explanations=[
                CropExplanation(crop_slug="maize", summary="Second"),
                CropExplanation(crop_slug="rice", summary="First"),
            ],
            disclaimer="Ignored",
        )
        normalized, reasons = service._normalize_response(response, templates, ["rice", "maize"])
        self.assertEqual([item.crop_slug for item in normalized.crop_explanations], ["rice", "maize"])
        self.assertEqual(reasons, [])

    def test_partial_llm_output_templates_only_missing_crop(self):
        service = AIService()
        candidates = [
            CropCandidate(crop_slug="rice", crop_name="Rice", candidate_sources=[CandidateSource.XGBOOST], model_probability=.7),
            CropCandidate(crop_slug="maize", crop_name="Maize", candidate_sources=[CandidateSource.XGBOOST], model_probability=.6),
        ]
        templates = service._template_response(candidates, DataQualityAssessment(level="medium"), "en")
        response = LLMExplanationResponse(
            crop_explanations=[CropExplanation(crop_slug="rice", summary="Kept explanation")],
            disclaimer="Ignored",
        )
        normalized, reasons = service._normalize_response(response, templates, ["rice", "maize"])
        self.assertEqual(normalized.crop_explanations[0].summary, "Kept explanation")
        self.assertEqual(normalized.crop_explanations[1].summary, templates.crop_explanations[1].summary)
        self.assertIn(ExplanationFailureCode.LLM_MISSING_CROP, reasons)

    def test_duplicate_llm_crop_is_rejected(self):
        response = LLMExplanationResponse(
            crop_explanations=[
                CropExplanation(crop_slug="rice", summary="One"),
                CropExplanation(crop_slug="Rice", summary="Two"),
            ],
            disclaimer="Test",
        )
        with self.assertRaises(ValueError) as raised:
            AIService()._normalize_response(response, response, ["rice"])
        self.assertEqual(raised.exception.code, ExplanationFailureCode.LLM_DUPLICATE_CROP)

    def test_unsafe_numeric_field_is_replaced_locally(self):
        service = AIService()
        candidate = CropCandidate(
            crop_slug="rice", crop_name="Rice", candidate_sources=[CandidateSource.XGBOOST], model_probability=.7
        )
        templates = service._template_response([candidate], DataQualityAssessment(level="medium"), "en")
        response = LLMExplanationResponse(
            crop_explanations=[
                CropExplanation(
                    crop_slug="rice",
                    summary="Safe summary",
                    why_recommended=["Expected yield is 5 tonnes", "Suitable from supplied evidence"],
                )
            ],
            disclaimer="Test",
        )
        normalized, reasons = service._normalize_response(response, templates, ["rice"])
        self.assertEqual(normalized.crop_explanations[0].summary, "Safe summary")
        self.assertEqual(normalized.crop_explanations[0].why_recommended, ["Suitable from supplied evidence"])
        self.assertIn(ExplanationFailureCode.LLM_UNSUPPORTED_NUMERIC_CLAIM, reasons)

    async def test_malformed_json_and_timeout_have_reason_codes(self):
        candidate = CropCandidate(
            crop_slug="rice", crop_name="Rice", candidate_sources=[CandidateSource.XGBOOST], model_probability=.7
        )
        quality = DataQualityAssessment(level="medium")
        malformed = AIService()
        malformed.enabled = True
        malformed.client = Mock()
        malformed.client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="not json"))]
        )
        malformed_result = await malformed.generate_crop_explanations([candidate], context(), quality)
        self.assertIn(ExplanationFailureCode.LLM_INVALID_JSON, malformed_result.reason_codes)

        timed_out = AIService()
        timed_out.enabled = True
        timed_out.client = Mock()
        timed_out.client.chat.completions.create.side_effect = TimeoutError()
        timeout_result = await timed_out.generate_crop_explanations([candidate], context(), quality)
        self.assertIn(ExplanationFailureCode.LLM_TIMEOUT, timeout_result.reason_codes)

    async def test_llm_schema_and_request_failures_have_reason_codes(self):
        candidate = CropCandidate(
            crop_slug="rice", crop_name="Rice", candidate_sources=[CandidateSource.XGBOOST], model_probability=.7
        )
        quality = DataQualityAssessment(level="medium")
        invalid_schema = AIService()
        invalid_schema.enabled = True
        invalid_schema.client = Mock()
        invalid_schema.client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"crop_explanations": []}'))]
        )
        schema_result = await invalid_schema.generate_crop_explanations(
            [candidate], context(), quality
        )
        self.assertIn(
            ExplanationFailureCode.LLM_SCHEMA_VALIDATION_FAILED,
            schema_result.reason_codes,
        )

        request_failure = AIService()
        request_failure.enabled = True
        request_failure.client = Mock()
        request_failure.client.chat.completions.create.side_effect = ConnectionError()
        request_result = await request_failure.generate_crop_explanations(
            [candidate], context(), quality
        )
        self.assertIn(ExplanationFailureCode.LLM_REQUEST_FAILED, request_result.reason_codes)

    async def test_missing_llm_api_key_has_reason_code(self):
        candidate = CropCandidate(
            crop_slug="rice", crop_name="Rice", candidate_sources=[CandidateSource.XGBOOST], model_probability=.7
        )
        with patch.dict("os.environ", {"GROQ_API_KEY": "", "ENABLE_LLM_EXPLANATIONS": "true"}), \
             patch("app.services.ai_service.load_dotenv"):
            service = AIService()
        result = await service.generate_crop_explanations(
            [candidate], context(), DataQualityAssessment(level="medium")
        )
        self.assertIn(ExplanationFailureCode.LLM_API_KEY_MISSING, result.reason_codes)

    def test_low_support_candidate_is_preliminary(self):
        candidate = CropCandidate(
            crop_slug="rice",
            crop_name="Rice",
            candidate_sources=[CandidateSource.XGBOOST],
            model_probability=.7,
        )
        ranked = crop_ranking_service.rank(
            [candidate], [], context(), DataQualityAssessment(level="medium"), ModelPredictionStatus.SUCCESS
        )
        self.assertEqual(ranked[0].recommendation_status, CandidateRecommendationStatus.PRELIMINARY)

    async def test_single_preliminary_response_is_not_padded(self):
        candidate = CropCandidate(
            crop_slug="rice", crop_name="Rice", candidate_sources=[CandidateSource.XGBOOST], model_probability=.7
        )
        model_result = CropModelResult(
            status=ModelPredictionStatus.SUCCESS,
            candidates=[candidate],
            model_version="test",
            model_supported_crop_count=22,
        )
        service = AIService()
        templates = service._template_response([candidate], DataQualityAssessment(level="medium"), "en")
        with patch.object(farm_context_service, "build", AsyncMock(return_value=(context(), DataQualityAssessment(level="medium")))), \
             patch.object(crop_prediction_service, "generate_candidates", AsyncMock(return_value=model_result)), \
             patch.object(AIService, "generate_crop_explanations", AsyncMock(return_value=ExplanationGenerationResult(templates, False))):
            response = await crop_recommendation_service.generate(Mock(), 1, 1, {}, "en")
        self.assertEqual(response.status, RecommendationStatus.PRELIMINARY)
        self.assertEqual(len(response.preliminary_crops), 1)
        self.assertEqual(response.recommended_crops, [])

    async def test_legacy_questionnaire_without_new_fields_is_readable(self):
        legacy_data = {
            "set_1": {"soil_texture": "loamy"},
            "set_2": {"soil_test_done": False, "fertilizer_type": "none"},
            "set_3": {"irrigation_type": "rainfed"},
            "set_4": {"state": "Maharashtra", "district": "Pune", "average_rainfall": 700},
            "set_5": {},
        }
        with patch.object(
            farm_context_service,
            "_weather",
            AsyncMock(return_value=(None, DataSource.UNKNOWN)),
        ):
            built, assessment = await farm_context_service.build(Mock(), 1, 1, legacy_data)
        self.assertIsNone(built.intended_sowing_date)
        self.assertEqual(built.rainfall_period, RainfallPeriod.ANNUAL)
        self.assertEqual(built.rainfall_compatibility, RainfallCompatibility.INCOMPATIBLE_PERIOD)
        self.assertEqual(assessment.level, DataQualityLevel.LOW)


if __name__ == "__main__":
    unittest.main()
