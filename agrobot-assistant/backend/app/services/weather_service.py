import httpx
import os
from typing import Dict, Any, Optional

class WeatherService:
    def __init__(self):
        self.api_key = os.getenv('OPENWEATHER_API_KEY')
        self.base_url = "http://api.openweathermap.org/data/2.5"
    
    async def get_current_weather(self, city: str, state: str) -> Optional[Dict[str, Any]]:
        """Get current weather data for a location"""
        if not self.api_key:
            return self._get_mock_weather_data()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/weather",
                    params={
                        "q": f"{city},{state},IN",
                        "appid": self.api_key,
                        "units": "metric"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "temperature": data["main"]["temp"],
                        "humidity": data["main"]["humidity"],
                        "pressure": data["main"]["pressure"],
                        "wind_speed": data["wind"]["speed"],
                        "description": data["weather"][0]["description"],
                        "visibility": data.get("visibility", 10000) / 1000  # Convert to km
                    }
                else:
                    return self._get_mock_weather_data()
                    
        except Exception as e:
            print(f"Weather API error: {e}")
            return self._get_mock_weather_data()
    
    async def get_weather_forecast(self, city: str, state: str) -> Optional[Dict[str, Any]]:
        """Get 5-day weather forecast"""
        if not self.api_key:
            return self._get_mock_forecast_data()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/forecast",
                    params={
                        "q": f"{city},{state},IN",
                        "appid": self.api_key,
                        "units": "metric"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Process forecast data
                    forecast = []
                    for item in data["list"][:5]:  # Next 5 days
                        forecast.append({
                            "date": item["dt_txt"],
                            "temperature": item["main"]["temp"],
                            "humidity": item["main"]["humidity"],
                            "description": item["weather"][0]["description"]
                        })
                    return {"forecast": forecast}
                else:
                    return self._get_mock_forecast_data()
                    
        except Exception as e:
            print(f"Forecast API error: {e}")
            return self._get_mock_forecast_data()
    
    def _get_mock_weather_data(self) -> Dict[str, Any]:
        """Mock weather data for development"""
        return {
            "temperature": 24,
            "humidity": 68,
            "pressure": 1013,
            "wind_speed": 12,
            "description": "partly cloudy",
            "visibility": 10
        }
    
    def _get_mock_forecast_data(self) -> Dict[str, Any]:
        """Mock forecast data for development"""
        return {
            "forecast": [
                {"date": "2025-05-30", "temperature": 26, "humidity": 65, "description": "sunny"},
                {"date": "2025-05-31", "temperature": 24, "humidity": 70, "description": "cloudy"},
                {"date": "2025-06-01", "temperature": 22, "humidity": 75, "description": "rainy"},
                {"date": "2025-06-02", "temperature": 25, "humidity": 68, "description": "sunny"},
                {"date": "2025-06-03", "temperature": 23, "humidity": 72, "description": "partly cloudy"}
            ]
        }

# Initialize weather service
weather_service = WeatherService()
