import os
from dotenv import load_dotenv
from groq import Groq
from app.models.recommendation import AIRecommendationResponse, CropRecommendation, CalendarEvent
from app.utils.prompt_generator import generate_farming_prompt
from app.services.crop_prediction_service import crop_prediction_service
from typing import Dict, Any
import json
import re
from datetime import datetime, date, timedelta
import logging

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=api_key) if api_key else None
        if not api_key:
            logger.warning("GROQ_API_KEY is not set; using fallback recommendation mode.")
        
    async def generate_farming_recommendations(self, user_data: Dict[str, Any]) -> AIRecommendationResponse:
        # Step 1: Get XGBoost crop predictions (non-blocking on failure)
        xgb_predictions = []
        try:
            xgb_predictions = await crop_prediction_service.predict_crops(user_data, top_n=5)
            if xgb_predictions:
                logger.info("XGBoost returned %d predictions: %s",
                            len(xgb_predictions),
                            [p["crop_name"] for p in xgb_predictions])
            else:
                logger.info("XGBoost returned no predictions; proceeding with LLM-only mode")
        except Exception as e:
            logger.warning("XGBoost prediction failed, falling back to LLM-only: %s", e)

        # Step 2: Generate prompt (includes XGBoost predictions when available)
        prompt = generate_farming_prompt(user_data, xgb_predictions=xgb_predictions or None)

        if self.client is None:
            return self._generate_fallback_response(user_data)
        
        try:
            # Call Groq API with Llama model
            completion = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert agricultural consultant.
                        IMPORTANT OUTPUT RULES:
                        - Return ONLY valid JSON.
                        - Do NOT repeat, quote, paraphrase, or restate the input prompt/context.
                        - Do NOT include headings like 'SOIL PHYSICAL PROPERTIES' or any template text from user prompt.
                        - Use the provided farm data to infer recommendations.

                        Return your response in this exact JSON schema:
                        {
                            "soil_health_score": 7.5,
                            "recommended_crops": [
                                {
                                    "crop_name": "Rice",
                                    "variety": "Basmati",
                                    "sowing_season": "Kharif",
                                    "expected_yield": "4-5 tons/hectare",
                                    "market_price_range": "₹2000-2500/quintal",
                                    "profitability_score": 7.5
                                }
                            ],
                            "farming_calendar": [
                                {
                                    "date": "2025-06-15",
                                    "activity": "Land Preparation",
                                    "description": "Prepare field for sowing",
                                    "priority": "high",
                                    "category": "sowing"
                                }
                            ],
                            "soil_improvement_tips": ["Add organic compost", "Test soil pH"],
                            "irrigation_recommendations": ["Use drip irrigation", "Monitor soil moisture"],
                            "fertilizer_recommendations": ["Apply NPK as per soil test"],
                            "pest_disease_prevention": ["Regular field inspection"]
                        }"""
                    },
                    {
                        "role": "user",
                        "content": f"Generate recommendations from the following farm profile. Do not echo this text.\\n\\n{prompt}"
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent JSON
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            # Get AI response - FIX: Added [0] to access first choice
            ai_response = completion.choices[0].message.content.strip()

            if self._looks_like_prompt_echo(ai_response):
                raise ValueError("Model response appears to echo prompt/template text")
            
            # Simple cleanup - remove any potential markdown
            ai_response = self._clean_response(ai_response)
            
            # Parse JSON directly
            parsed_response = json.loads(ai_response)

            # Personalize tips using questionnaire signals (even when LLM succeeds)
            parsed_response = self._personalize_recommendation_lists(user_data, parsed_response)
            
            # Convert to Pydantic models
            recommendations = AIRecommendationResponse(
                user_id=user_data["user_id"],
                soil_health_score=parsed_response.get("soil_health_score", 7.0),
                recommended_crops=[
                    CropRecommendation(**crop) for crop in parsed_response.get("recommended_crops", [])
                ],
                farming_calendar=[
                    CalendarEvent(**event) for event in parsed_response.get("farming_calendar", [])
                ],
                soil_improvement_tips=parsed_response.get("soil_improvement_tips", []),
                irrigation_recommendations=parsed_response.get("irrigation_recommendations", []),
                fertilizer_recommendations=parsed_response.get("fertilizer_recommendations", []),
                pest_disease_prevention=parsed_response.get("pest_disease_prevention", []),
                generated_at=datetime.now(),
                next_review_date=date.today() + timedelta(days=30)
            )
            
            return recommendations
                
        except Exception as e:
            logger.exception("Error calling Groq API: %s", e)
            return self._generate_fallback_response(user_data)

    def _personalize_recommendation_lists(self, user_data: Dict[str, Any], parsed_response: Dict[str, Any]) -> Dict[str, Any]:
        soil_physical = user_data.get("set_1", {})
        soil_fertility = user_data.get("set_2", {})
        moisture_irrigation = user_data.get("set_3", {})
        environmental = user_data.get("set_4", {})
        organic_practices = user_data.get("set_5", {})

        texture = str(soil_physical.get("soil_texture", "")).lower()
        water_retention = str(soil_physical.get("water_retention", "")).lower()
        irrigation_type = str(moisture_irrigation.get("irrigation_type", "")).lower()
        watering_frequency = str(moisture_irrigation.get("watering_frequency", "")).lower()
        rainfall = self._safe_float(environmental.get("average_rainfall")) or 0
        temperature = self._safe_float(environmental.get("average_temperature")) or 0
        uses_organic = bool(organic_practices.get("uses_organic_matter"))

        soil_tips = list(parsed_response.get("soil_improvement_tips", []))
        irrigation_tips = list(parsed_response.get("irrigation_recommendations", []))

        if "sandy" in texture:
            soil_tips.append("Increase organic compost and mulch to improve moisture holding in sandy soils")
        if "clay" in texture:
            soil_tips.append("Add well-decomposed organic matter and maintain drainage channels to reduce clay compaction")
        if "loam" in texture:
            soil_tips.append("Maintain loam balance with residue incorporation and periodic soil testing")

        if "low" in water_retention:
            soil_tips.append("Use mulching and split irrigation to reduce deep percolation losses")
        if "high" in water_retention:
            soil_tips.append("Avoid over-irrigation and create surface drains to prevent waterlogging")

        if not uses_organic:
            soil_tips.append("Introduce FYM/compost at least once per season to improve long-term soil structure")

        n_score = self._map_level(soil_fertility.get("npk_nitrogen"))
        p_score = self._map_level(soil_fertility.get("npk_phosphorus"))
        k_score = self._map_level(soil_fertility.get("npk_potassium"))
        if n_score < 0.4:
            soil_tips.append("Low nitrogen detected: include legume rotation and split N application")
        if p_score < 0.4:
            soil_tips.append("Low phosphorus detected: apply basal phosphorus near root zone during sowing")
        if k_score < 0.4:
            soil_tips.append("Low potassium detected: prioritize potash for stress tolerance and grain filling")

        if "drip" in irrigation_type:
            irrigation_tips.append("Use fertigation schedule with drip to improve nutrient-use efficiency")
        elif "sprinkler" in irrigation_type:
            irrigation_tips.append("Run sprinklers during low-wind windows to improve uniform distribution")
        elif irrigation_type:
            irrigation_tips.append("Shift towards scheduled irrigation intervals based on crop stage and soil moisture")

        if "daily" in watering_frequency:
            irrigation_tips.append("Reduce daily irrigation volume and use moisture checks to avoid root-zone saturation")
        elif "weekly" in watering_frequency:
            irrigation_tips.append("Split weekly irrigation into smaller events during high-temperature periods")

        if rainfall and rainfall >= 1200:
            irrigation_tips.append("With high rainfall, prioritize drainage and irrigate only during dry spells")
        elif rainfall and rainfall <= 700:
            irrigation_tips.append("With low rainfall, use mulching and early-morning irrigation to reduce evaporation")

        if temperature and temperature >= 34:
            irrigation_tips.append("During heat stress, irrigate in early morning and maintain light surface mulch")

        def _dedupe_keep_order(items):
            seen = set()
            out = []
            for item in items:
                text = str(item).strip()
                if not text:
                    continue
                key = text.lower()
                if key in seen:
                    continue
                seen.add(key)
                out.append(text)
            return out

        parsed_response["soil_improvement_tips"] = _dedupe_keep_order(soil_tips)[:8]
        parsed_response["irrigation_recommendations"] = _dedupe_keep_order(irrigation_tips)[:8]
        return parsed_response

    def _looks_like_prompt_echo(self, response_text: str) -> bool:
        text = (response_text or "").lower()
        echo_markers = [
            "i am a farmer seeking agricultural advice",
            "soil physical properties",
            "soil fertility & nutrients",
            "moisture & irrigation",
            "environmental & regional",
            "based on this information, please provide",
            "focus on sustainable and profitable farming methods",
        ]
        return any(marker in text for marker in echo_markers)
    
    def _clean_response(self, response: str) -> str:
        """Simple cleanup of AI response"""
        # Remove common markdown patterns
        response = re.sub(r"```(?:json)?\s*", "", response)
        response = response.replace("```", "")
        response = response.strip()
        
        # Find JSON object boundaries
        start = response.find('{')
        end = response.rfind('}') + 1
        
        if start != -1 and end != 0:
            return response[start:end]
        
        return response

    def _safe_float(self, value):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip()
        if not text:
            return None
        match = re.search(r"-?\d+(\.\d+)?", text)
        if not match:
            return None
        try:
            return float(match.group(0))
        except ValueError:
            return None

    def _map_level(self, value):
        if value is None:
            return 0.5
        text = str(value).strip().lower()
        if text in {"low", "deficient", "poor", "very low"}:
            return 0.2
        if text in {"medium", "moderate", "normal", "average"}:
            return 0.6
        if text in {"high", "good", "rich", "very high"}:
            return 0.9

        numeric = self._safe_float(value)
        if numeric is None:
            return 0.5
        if numeric <= 25:
            return 0.2
        if numeric <= 50:
            return 0.5
        if numeric <= 75:
            return 0.7
        return 0.9

    def _candidate_crops(self, texture: str, rainfall: float, irrigation: str, temperature: float):
        candidates = []

        if rainfall >= 1100:
            candidates.extend([("Rice", "Swarna", "Kharif", "4-6 tons/hectare"), ("Sugarcane", "Co-0238", "Annual", "70-90 tons/hectare")])
        elif rainfall <= 700:
            candidates.extend([("Pearl Millet", "HHB 67", "Kharif", "2-3 tons/hectare"), ("Chickpea", "JG 11", "Rabi", "1.5-2.2 tons/hectare")])
        else:
            candidates.extend([("Maize", "DHM-117", "Kharif", "4-5 tons/hectare"), ("Wheat", "HD-2967", "Rabi", "3-4.5 tons/hectare")])

        if "sandy" in texture:
            candidates.extend([("Groundnut", "GG 20", "Kharif", "2-3 tons/hectare"), ("Mustard", "Pusa Bold", "Rabi", "1.2-1.8 tons/hectare")])
        if "clay" in texture or "black" in texture:
            candidates.extend([("Cotton", "Bt Hybrid", "Kharif", "2-3 tons/hectare"), ("Soybean", "JS 95-60", "Kharif", "2-2.8 tons/hectare")])
        if "loam" in texture:
            candidates.extend([("Tomato", "Arka Rakshak", "Year-round", "30-40 tons/hectare"), ("Onion", "N-53", "Rabi", "20-30 tons/hectare")])

        if any(x in irrigation for x in ["drip", "sprinkler"]):
            candidates.extend([("Chili", "Tejaswini", "Year-round", "8-12 tons/hectare"), ("Tomato", "Arka Samrat", "Year-round", "35-45 tons/hectare")])

        if temperature >= 32:
            candidates.extend([("Sorghum", "CSV 15", "Kharif", "2.5-3.5 tons/hectare")])
        if temperature <= 22:
            candidates.extend([("Potato", "Kufri Jyoti", "Rabi", "20-28 tons/hectare")])

        seen = set()
        unique = []
        for crop in candidates:
            if crop[0] in seen:
                continue
            seen.add(crop[0])
            unique.append(crop)
        return unique[:3]
    
    def _generate_fallback_response(self, user_data: Dict[str, Any]) -> AIRecommendationResponse:
        """Generate data-driven fallback recommendations when AI service fails."""
        logger.warning("Using data-driven fallback recommendation mode for user %s", user_data.get("user_id"))

        soil_physical = user_data.get("set_1", {})
        soil_fertility = user_data.get("set_2", {})
        moisture_irrigation = user_data.get("set_3", {})
        environmental = user_data.get("set_4", {})
        organic_practices = user_data.get("set_5", {})

        texture = str(soil_physical.get("soil_texture", "")).lower()
        irrigation = str(moisture_irrigation.get("irrigation_type", "")).lower()
        rainfall = self._safe_float(environmental.get("average_rainfall")) or 850.0
        temperature = self._safe_float(environmental.get("average_temperature")) or 27.0

        n_score = self._map_level(soil_fertility.get("npk_nitrogen"))
        p_score = self._map_level(soil_fertility.get("npk_phosphorus"))
        k_score = self._map_level(soil_fertility.get("npk_potassium"))
        fertility_score = (n_score + p_score + k_score) / 3

        organic_bonus = 0.5 if organic_practices.get("uses_organic_matter") else 0
        earthworm_bonus = 0.4 if organic_practices.get("earthworms_present") else 0
        soil_health = max(4.5, min(9.6, 5.5 + fertility_score * 3 + organic_bonus + earthworm_bonus))

        selected_crops = self._candidate_crops(texture, rainfall, irrigation, temperature)
        if not selected_crops:
            selected_crops = [
                ("Maize", "DHM-117", "Kharif", "4-5 tons/hectare"),
                ("Wheat", "HD-2967", "Rabi", "3-4.5 tons/hectare"),
                ("Chickpea", "JG 11", "Rabi", "1.5-2.2 tons/hectare"),
            ]

        crop_models = []
        for idx, (crop_name, variety, season, yield_text) in enumerate(selected_crops):
            crop_models.append(
                CropRecommendation(
                    crop_name=crop_name,
                    variety=variety,
                    sowing_season=season,
                    expected_yield=yield_text,
                    market_price_range="₹1800-3200/quintal",
                    profitability_score=round(max(6.0, min(9.5, soil_health - 0.6 + (idx * 0.2))), 1),
                )
            )

        today = date.today()
        calendar = [
            CalendarEvent(
                date=today + timedelta(days=5),
                activity="Land Preparation",
                description="Prepare field based on current soil moisture and texture conditions",
                priority="high",
                category="sowing",
            ),
            CalendarEvent(
                date=today + timedelta(days=12),
                activity=f"Sow {selected_crops[0][0]} ({selected_crops[0][1]})",
                description="Use seed treatment and line sowing for better germination",
                priority="high",
                category="sowing",
            ),
            CalendarEvent(
                date=today + timedelta(days=24),
                activity="Nutrient Application",
                description="Apply fertilizer split based on NPK status from questionnaire",
                priority="high",
                category="fertilizing",
            ),
            CalendarEvent(
                date=today + timedelta(days=36),
                activity="Irrigation Scheduling",
                description="Adjust irrigation interval according to local rainfall and evapotranspiration",
                priority="medium",
                category="irrigation",
            ),
            CalendarEvent(
                date=today + timedelta(days=52),
                activity="Pest and Disease Scouting",
                description="Inspect crop canopy and apply IPM only if threshold is crossed",
                priority="medium",
                category="pest_control",
            ),
            CalendarEvent(
                date=today + timedelta(days=110),
                activity="Harvest Planning",
                description="Plan harvest and market linkage based on maturity and price trends",
                priority="high",
                category="harvesting",
            ),
        ]

        fertilizer_recs = [
            "Apply basal NPK dose based on your soil test/observed fertility status",
            "Split nitrogen into 2-3 applications to improve uptake and reduce losses",
            "Use compost or FYM to improve nutrient retention and microbial activity",
        ]
        if n_score < 0.4:
            fertilizer_recs.append("Nitrogen appears low; prioritize urea/organic-N in split doses")
        if p_score < 0.4:
            fertilizer_recs.append("Phosphorus appears low; apply SSP/DAP at sowing")
        if k_score < 0.4:
            fertilizer_recs.append("Potassium appears low; apply MOP to improve stress tolerance")

        irrigation_recs = [
            "Irrigate based on soil moisture checks rather than fixed daily scheduling",
            "Avoid over-irrigation to reduce root stress and nutrient leaching",
            "Use mulching to conserve moisture and suppress weeds",
        ]
        if any(x in irrigation for x in ["drip", "sprinkler"]):
            irrigation_recs.append("Maintain emitter/nozzle uniformity and flush lines regularly")

        return AIRecommendationResponse(
            user_id=user_data["user_id"],
            soil_health_score=round(soil_health, 1),
            recommended_crops=crop_models,
            farming_calendar=calendar,
            soil_improvement_tips=[
                "Incorporate crop residues and organic matter to improve soil structure",
                "Maintain pH in the optimal range through periodic soil testing",
                "Use crop rotation (cereal-legume sequence) to stabilize soil fertility",
            ],
            irrigation_recommendations=irrigation_recs,
            fertilizer_recommendations=fertilizer_recs,
            pest_disease_prevention=[
                "Scout fields weekly and use threshold-based pest control",
                "Use certified seeds and treat seeds before sowing",
                "Improve field sanitation and remove infected plant debris",
            ],
            generated_at=datetime.now(),
            next_review_date=date.today() + timedelta(days=30),
        )

# Initialize AI service
ai_service = AIService()
