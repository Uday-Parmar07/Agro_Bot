from typing import Dict, Any
import json


def generate_farming_prompt(user_data: Dict[str, Any]) -> str:
   """Generate a compact profile prompt from questionnaire data."""

   soil_physical = user_data.get("set_1", {})
   soil_fertility = user_data.get("set_2", {})
   moisture_irrigation = user_data.get("set_3", {})
   environmental = user_data.get("set_4", {})
   organic_practices = user_data.get("set_5", {})

   profile = {
      "soil_physical": {
         "soil_texture": soil_physical.get("soil_texture", "Not specified"),
         "water_retention": soil_physical.get("water_retention", "Not specified"),
         "soil_top_layer": soil_physical.get("soil_top_layer", "Not specified"),
      },
      "soil_fertility": {
         "soil_test_done": soil_fertility.get("soil_test_done", "No"),
         "npk_nitrogen": soil_fertility.get("npk_nitrogen", "Unknown"),
         "npk_phosphorus": soil_fertility.get("npk_phosphorus", "Unknown"),
         "npk_potassium": soil_fertility.get("npk_potassium", "Unknown"),
         "yellowing_slow_growth": soil_fertility.get("yellowing_slow_growth", "No"),
         "fertilizer_type": soil_fertility.get("fertilizer_type", "Not specified"),
      },
      "moisture_irrigation": {
         "irrigation_type": moisture_irrigation.get("irrigation_type", "Not specified"),
         "watering_frequency": moisture_irrigation.get("watering_frequency", "Not specified"),
      },
      "environmental": {
         "district": environmental.get("district", "Not specified"),
         "state": environmental.get("state", "Not specified"),
         "average_rainfall": environmental.get("average_rainfall", "Not specified"),
         "average_temperature": environmental.get("average_temperature", "Not specified"),
         "total_area": environmental.get("total_area", "Not specified"),
         "area_unit": environmental.get("area_unit", ""),
      },
      "organic_practices": {
         "uses_organic_matter": organic_practices.get("uses_organic_matter", "No"),
         "organic_matter_types": organic_practices.get("organic_matter_types", []),
         "crop_residue_practice": organic_practices.get("crop_residue_practice", "Not specified"),
         "earthworms_present": organic_practices.get("earthworms_present", "No"),
      },
   }

   prompt = (
      "Farm profile JSON (use this data only, do not repeat/copy the text; infer recommendations):\n"
      + json.dumps(profile, ensure_ascii=False)
   )

   return prompt.strip()
