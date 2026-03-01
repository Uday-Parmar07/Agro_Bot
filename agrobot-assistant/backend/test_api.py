import asyncio
import os
from dotenv import load_dotenv
from app.services.ai_service import ai_service

load_dotenv()

async def test_ai():
    # Test data
    user_data = {
        "user_id": 1,
        "set_1": {
            "soil_texture": "loamy",
            "water_retention": "moderate",
            "soil_top_layer": "dark_crumbly"
        },
        "set_2": {
            "soil_test_done": True,
            "npk_nitrogen": 50,
            "npk_phosphorus": 30,
            "npk_potassium": 40,
            "yellowing_slow_growth": False,
            "fertilizer_type": "organic"
        },
        "set_3": {
            "irrigation_type": "drip",
            "watering_frequency": "weekly"
        },
        "set_4": {
            "state": "Maharashtra",
            "district": "Pune",
            "average_rainfall": 600,
            "average_temperature": 25,
            "total_area": 5,
            "area_unit": "acre"
        },
        "set_5": {
            "uses_organic_matter": True,
            "organic_matter_types": ["compost", "green_manure"],
            "crop_residue_practice": "leave_in_field",
            "earthworms_present": True
        }
    }
    
    try:
        print("Testing AI service...")
        recommendations = await ai_service.generate_farming_recommendations(user_data)
        print("Success! Recommendations generated:")
        print(f"Soil Health Score: {recommendations.soil_health_score}")
        print(f"Recommended Crops: {len(recommendations.recommended_crops)}")
        print(f"Calendar Events: {len(recommendations.farming_calendar)}")
        return True
    except Exception as e:
        print(f"AI Service Error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_ai())
