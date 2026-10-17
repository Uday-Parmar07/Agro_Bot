import copy
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.schemas import Base, Farm, QuestionnaireResponse, Recommendation, User
from app.models.farm_context import DataQualityAssessment, FarmContext
from app.models.recommendation import CropModelResult, ModelPredictionStatus
from app.routers.farms import get_farm_assessment
from app.routers.recommendations import _db_to_response_model, _save_recommendation
from app.services.analytics_service import build_analytics_overview
from app.services.crop_recommendation_service import crop_recommendation_service
from app.services.soil_assessment_service import assess_soil


def answers():
    return {
        "set_1": {"soil_top_layer": "mixed", "water_retention": "moderate"},
        "set_2": {"soil_test_done": False, "yellowing_slow_growth": False},
        "set_5": {"uses_organic_matter": True, "crop_residue_practice": "remove", "earthworms_present": True},
    }


class SoilAssessmentTests(unittest.TestCase):
    def test_complete_questionnaire_without_lab_has_explicit_estimated_score(self):
        result = assess_soil(answers())
        self.assertEqual(result.score, 8.3)
        self.assertEqual(result.status, "estimated")
        self.assertEqual(len(result.components), 6)
        self.assertIn("not a laboratory", result.explanation)

    def test_missing_and_invalid_answers_do_not_receive_defaults(self):
        for value in (None, "false", 0, [], {}, "unknown"):
            with self.subTest(value=value):
                data = answers()
                data["set_2"]["yellowing_slow_growth"] = value
                result = assess_soil(data)
                self.assertIsNone(result.score)
                self.assertEqual(result.missing_fields, ["yellowing_slow_growth"])
        self.assertEqual(len(assess_soil({}).missing_fields), 6)
        self.assertIsNone(assess_soil({"set_1": []}).score)

    def test_false_answers_are_scored_and_unrelated_inputs_do_not_change_score(self):
        data = answers()
        data["set_5"]["uses_organic_matter"] = False
        data["set_5"]["earthworms_present"] = False
        baseline = assess_soil(data)
        self.assertEqual(baseline.score, 5.0)
        enriched = copy.deepcopy(data)
        enriched["set_2"].update(soil_test_done=True, npk_nitrogen=999, soil_ph=6.5)
        enriched["set_4"] = {"average_rainfall": 9999}
        self.assertEqual(assess_soil(enriched), baseline)


class SavedSoilAssessmentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.user = User(email="soil@test.local", hashed_password="test", full_name="Farmer")
        self.other = User(email="other@test.local", hashed_password="test", full_name="Other")
        self.db.add_all([self.user, self.other])
        self.db.flush()
        self.farm = Farm(user_id=self.user.id, name="Saved Farm")
        self.empty_farm = Farm(user_id=self.user.id, name="Empty Farm")
        self.db.add_all([self.farm, self.empty_farm])
        self.db.flush()
        for key, value in answers().items():
            self.db.add(QuestionnaireResponse(
                user_id=self.user.id, farm_id=self.farm.id,
                set_number=int(key[-1]), answers=value,
            ))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    async def test_existing_answers_work_without_any_recommendation_and_remain_farm_scoped(self):
        result = await get_farm_assessment(self.farm.id, self.user, self.db)
        self.assertEqual(result.score, 8.3)
        empty = await get_farm_assessment(self.empty_farm.id, self.user, self.db)
        self.assertIsNone(empty.score)
        self.assertEqual(self.db.query(Recommendation).count(), 0)
        with self.assertRaises(HTTPException) as raised:
            await get_farm_assessment(self.farm.id, self.other, self.db)
        self.assertEqual(raised.exception.status_code, 404)

    async def test_analytics_uses_updated_answers_without_backdating_history(self):
        overview = build_analytics_overview(self.db, self.farm.id)
        self.assertEqual(overview.latest_soil_health_score, 8.3)
        self.assertEqual(overview.soil_score_trend, [])
        row = self.db.query(QuestionnaireResponse).filter_by(farm_id=self.farm.id, set_number=5).one()
        row.answers = {**row.answers, "earthworms_present": False}
        self.db.commit()
        self.assertEqual(build_analytics_overview(self.db, self.farm.id).latest_soil_health_score, 6.7)

    async def test_no_crop_candidates_still_generates_and_persists_soil_score(self):
        context = FarmContext(farm_id=self.farm.id, user_id=self.user.id)
        target = "app.services.crop_recommendation_service"
        with patch(f"{target}.farm_context_service.build", AsyncMock(return_value=(context, DataQualityAssessment(level="low")))), \
             patch(f"{target}.crop_prediction_service.generate_candidates", AsyncMock(return_value=CropModelResult(status=ModelPredictionStatus.MODEL_UNAVAILABLE))), \
             patch(f"{target}.crop_catalog_service.find_knowledge_candidates", return_value=[]), \
             patch(f"{target}.ai_service.generate_crop_explanations", AsyncMock()) as llm:
            response = await crop_recommendation_service.generate(self.db, self.farm.id, self.user.id, answers(), "en")
        llm.assert_not_called()
        self.assertEqual(response.soil_health_score, 8.3)
        record = _save_recommendation(self.db, self.user.id, self.farm.id, response)
        self.assertEqual(_db_to_response_model(record).soil_health_score, 8.3)
        self.assertEqual(record.input_snapshot["soil_assessment"]["method_version"], "soil-observations-v1")
        self.assertEqual(build_analytics_overview(self.db, self.farm.id).soil_score_trend[0].score, 8.3)
