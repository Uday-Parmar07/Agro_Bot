import asyncio
import os
from dotenv import load_dotenv
from app.models.farm_context import (
    DataSource,
    FarmContext,
    RainfallCompatibility,
    RainfallPeriod,
)
from app.services.crop_prediction_service import crop_prediction_service

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
        context = FarmContext(
            farm_id=1,
            user_id=1,
            state="Maharashtra",
            district="Pune",
            soil_type="loamy",
            irrigation_method="drip",
            nitrogen=50,
            phosphorus=30,
            potassium=40,
            ph=6.5,
            temperature=25,
            humidity=65,
            rainfall_value=200,
            rainfall_period=RainfallPeriod.TRAINING_DATASET_UNSPECIFIED,
            rainfall_compatibility=RainfallCompatibility.COMPATIBLE,
            model_compatible_rainfall_mm=200,
            npk_source=DataSource.LABORATORY_TEST,
            ph_source=DataSource.LABORATORY_TEST,
            temperature_source=DataSource.FARMER_PROVIDED,
            humidity_source=DataSource.WEATHER_API,
            rainfall_source=DataSource.FARMER_PROVIDED,
            weather_source=DataSource.WEATHER_API,
        )
        result = await crop_prediction_service.generate_candidates(context)
        print("Success! Model candidates generated:")
        print(f"Status: {result.status.value}")
        print(f"Supported classes: {result.model_supported_crop_count}")
        print(f"Candidates: {len(result.candidates)}")
        return True
    except Exception as e:
        print(f"AI Service Error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_ai())
