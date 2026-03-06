import os
from dotenv import load_dotenv
from groq import Groq
from app.models.recommendation import AIRecommendationResponse, CropRecommendation, CalendarEvent
from app.utils.prompt_generator import generate_farming_prompt
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
        # Generate comprehensive prompt from user questionnaire data
        prompt = generate_farming_prompt(user_data)

        if self.client is None:
            return self._generate_fallback_response(user_data)
        
        try:
            # Call Groq API with Llama model
            completion = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert agricultural consultant. 
                        IMPORTANT: Return ONLY valid JSON without any markdown formatting, explanations, or code blocks.
                        
                        Return your response in this exact JSON format:
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
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent JSON
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            # Get AI response - FIX: Added [0] to access first choice
            ai_response = completion.choices[0].message.content.strip()
            
            # Simple cleanup - remove any potential markdown
            ai_response = self._clean_response(ai_response)
            
            # Parse JSON directly
            parsed_response = json.loads(ai_response)
            
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
    
    def _generate_fallback_response(self, user_data: Dict[str, Any]) -> AIRecommendationResponse:
        """Generate a basic fallback response if AI service fails"""
        return AIRecommendationResponse(
            user_id=user_data["user_id"],
            soil_health_score=8.2,
            recommended_crops=[
                CropRecommendation(
                    crop_name="Rice",
                    variety="Basmati",
                    sowing_season="Kharif",
                    expected_yield="4-5 tons/hectare",
                    market_price_range="₹2000-2500/quintal",
                    profitability_score=7.5
                ),
                CropRecommendation(
                    crop_name="Wheat",
                    variety="HD-2967",
                    sowing_season="Rabi",
                    expected_yield="3-4 tons/hectare",
                    market_price_range="₹1800-2200/quintal",
                    profitability_score=7.0
                ),
                CropRecommendation(
                    crop_name="Tomato",
                    variety="Hybrid",
                    sowing_season="Year-round",
                    expected_yield="25-30 tons/hectare",
                    market_price_range="₹800-1200/quintal",
                    profitability_score=8.5
                )
            ],
            farming_calendar=[
                CalendarEvent(
                    date=date.today() + timedelta(days=7),
                    activity="Soil Preparation",
                    description="Prepare the field for sowing",
                    priority="high",
                    category="sowing"
                ),
                CalendarEvent(
                    date=date.today() + timedelta(days=14),
                    activity="Sowing",
                    description="Sow seeds in prepared field",
                    priority="high",
                    category="sowing"
                ),
                CalendarEvent(
                    date=date.today() + timedelta(days=30),
                    activity="First Irrigation",
                    description="Provide first irrigation after sowing",
                    priority="medium",
                    category="irrigation"
                ),
                CalendarEvent(
                    date=date.today() + timedelta(days=45),
                    activity="Fertilizer Application",
                    description="Apply NPK fertilizer as per soil test",
                    priority="high",
                    category="fertilizing"
                ),
                CalendarEvent(
                    date=date.today() + timedelta(days=60),
                    activity="Pest Monitoring",
                    description="Check for pest and disease symptoms",
                    priority="medium",
                    category="pest_control"
                ),
                CalendarEvent(
                    date=date.today() + timedelta(days=120),
                    activity="Harvesting",
                    description="Harvest mature crops",
                    priority="high",
                    category="harvesting"
                )
            ],
            soil_improvement_tips=[
                "Add organic compost to improve soil structure and fertility",
                "Test soil pH regularly and maintain between 6.0-7.5",
                "Practice crop rotation to maintain soil health",
                "Use green manure crops during off-season",
                "Implement proper drainage to prevent waterlogging"
            ],
            irrigation_recommendations=[
                "Use drip irrigation for water efficiency",
                "Monitor soil moisture levels regularly",
                "Irrigate early morning or evening to reduce evaporation",
                "Maintain proper drainage channels",
                "Apply mulching to retain soil moisture"
            ],
            fertilizer_recommendations=[
                "Apply NPK fertilizers based on soil test results",
                "Use organic fertilizers like compost and vermicompost",
                "Apply micronutrients if deficiency is detected",
                "Follow recommended dosage to avoid over-fertilization",
                "Time fertilizer application with crop growth stages"
            ],
            pest_disease_prevention=[
                "Regular field inspection for early detection",
                "Use Integrated Pest Management (IPM) practices",
                "Maintain field hygiene and remove crop residues",
                "Use resistant varieties when available",
                "Apply biological control methods when possible"
            ],
            generated_at=datetime.now(),
            next_review_date=date.today() + timedelta(days=30)
        )

# Initialize AI service
ai_service = AIService()
