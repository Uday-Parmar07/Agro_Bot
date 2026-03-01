from typing import Dict, Any

def generate_farming_prompt(user_data: Dict[str, Any]) -> str:
    """
    Generate a comprehensive prompt for the AI model based on user questionnaire data
    """
    
    # Extract data from different questionnaire sets
    soil_physical = user_data.get("set_1", {})
    soil_fertility = user_data.get("set_2", {})
    moisture_irrigation = user_data.get("set_3", {})
    environmental = user_data.get("set_4", {})
    organic_practices = user_data.get("set_5", {})
    
    prompt = f"""
    I am a farmer seeking agricultural advice. Here are the details about my farm:

    🧪 SOIL PHYSICAL PROPERTIES:
    - Soil Texture: {soil_physical.get('soil_texture', 'Not specified')}
    - Water Retention: {soil_physical.get('water_retention', 'Not specified')}
    - Top Layer Condition: {soil_physical.get('soil_top_layer', 'Not specified')}

    🌱 SOIL FERTILITY & NUTRIENTS:
    - Soil Test Done: {soil_fertility.get('soil_test_done', 'No')}
    - NPK Levels: N-{soil_fertility.get('npk_nitrogen', 'Unknown')}, P-{soil_fertility.get('npk_phosphorus', 'Unknown')}, K-{soil_fertility.get('npk_potassium', 'Unknown')}
    - Yellowing/Slow Growth Observed: {soil_fertility.get('yellowing_slow_growth', 'No')}
    - Current Fertilizer Type: {soil_fertility.get('fertilizer_type', 'Not specified')}

    💧 MOISTURE & IRRIGATION:
    - Irrigation Method: {moisture_irrigation.get('irrigation_type', 'Not specified')}
    - Watering Frequency: {moisture_irrigation.get('watering_frequency', 'Not specified')}

    🌍 ENVIRONMENTAL & REGIONAL:
    - Location: {environmental.get('district', 'Not specified')}, {environmental.get('state', 'Not specified')}
    - Average Rainfall: {environmental.get('average_rainfall', 'Not specified')} mm/year
    - Average Temperature: {environmental.get('average_temperature', 'Not specified')}°C
    - Total Farm Area: {environmental.get('total_area', 'Not specified')} {environmental.get('area_unit', '')}

    🌿 ORGANIC MATTER & PRACTICES:
    - Uses Organic Matter: {organic_practices.get('uses_organic_matter', 'No')}
    - Organic Matter Types: {', '.join(organic_practices.get('organic_matter_types', []))}
    - Crop Residue Practice: {organic_practices.get('crop_residue_practice', 'Not specified')}
    - Earthworms Present: {organic_practices.get('earthworms_present', 'No')}

    Based on this information, please provide:

    1. A soil health assessment score (0-10)
    2. Top 3 recommended crops suitable for my conditions with varieties, expected yield, and market prices
    3. A detailed farming calendar for the next 6 months with specific dates for:
       - Land preparation
       - Sowing/planting
       - Fertilizer application
       - Irrigation schedule
       - Pest control measures
       - Harvesting
    4. Specific soil improvement recommendations
    5. Irrigation optimization suggestions
    6. Fertilizer recommendations based on my soil condition
    7. Pest and disease prevention strategies

    Please consider the local climate, soil conditions, and current farming practices in your recommendations.
    Focus on sustainable and profitable farming methods suitable for Indian agriculture.
    """
    
    return prompt.strip()
