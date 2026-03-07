import httpx
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import hashlib

class WeatherService:
    def __init__(self):
        self.api_key = os.getenv('OPENWEATHER_API_KEY')
        self.base_url = "http://api.openweathermap.org/data/2.5"
    
    async def get_current_weather(self, city: str, state: str) -> Optional[Dict[str, Any]]:
        """Get current weather data for a location"""
        if not self.api_key:
            return self._get_mock_weather_data(city, state)
        
        try:
            query_variants = [
                f"{city},{state},IN",
                f"{city},IN",
                f"{state},IN",
            ]

            async with httpx.AsyncClient() as client:
                response = None
                for query in query_variants:
                    response = await client.get(
                        f"{self.base_url}/weather",
                        params={
                            "q": query,
                            "appid": self.api_key,
                            "units": "metric"
                        }
                    )
                    if response.status_code == 200:
                        break
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "temperature": data["main"]["temp"],
                        "humidity": data["main"]["humidity"],
                        "pressure": data["main"]["pressure"],
                        "wind_speed": data["wind"]["speed"],
                        "description": data["weather"][0]["description"],
                        "visibility": data.get("visibility", 10000) / 1000,  # Convert to km
                        "location": data.get("name") or f"{city}, {state}"
                    }
                else:
                    return self._get_mock_weather_data(city, state)
                    
        except Exception as e:
            print(f"Weather API error: {e}")
            return self._get_mock_weather_data(city, state)
    
    async def get_weather_forecast(self, city: str, state: str) -> Optional[Dict[str, Any]]:
        """Get 5-day weather forecast"""
        if not self.api_key:
            return self._get_mock_forecast_data(city, state)
        
        try:
            query_variants = [
                f"{city},{state},IN",
                f"{city},IN",
                f"{state},IN",
            ]

            async with httpx.AsyncClient() as client:
                response = None
                for query in query_variants:
                    response = await client.get(
                        f"{self.base_url}/forecast",
                        params={
                            "q": query,
                            "appid": self.api_key,
                            "units": "metric"
                        }
                    )
                    if response.status_code == 200:
                        break
                
                if response.status_code == 200:
                    data = response.json()
                    # Build a compact 3-day forecast by picking one representative entry per day
                    forecast = []
                    seen_days = set()
                    for item in data.get("list", []):
                        dt_text = item.get("dt_txt", "")
                        day_key = dt_text.split(" ")[0] if dt_text else None
                        if not day_key or day_key in seen_days:
                            continue
                        seen_days.add(day_key)
                        forecast.append({
                            "date": dt_text,
                            "temperature": item["main"]["temp"],
                            "humidity": item["main"]["humidity"],
                            "description": item["weather"][0]["description"]
                        })
                        if len(forecast) == 3:
                            break
                    return {
                        "forecast": forecast,
                        "location": data.get("city", {}).get("name") or f"{city}, {state}"
                    }
                else:
                    return self._get_mock_forecast_data(city, state)
                    
        except Exception as e:
            print(f"Forecast API error: {e}")
            return self._get_mock_forecast_data(city, state)
    
    def _loc_seed(self, city: str, state: str) -> int:
        key = f"{city}|{state}".lower().encode("utf-8")
        digest = hashlib.md5(key).hexdigest()[:8]
        return int(digest, 16)

    def _get_mock_weather_data(self, city: str, state: str) -> Dict[str, Any]:
        """Mock weather data for development, varied by location."""
        seed = self._loc_seed(city, state)
        temperature = 18 + (seed % 16)
        humidity = 45 + (seed % 40)
        wind_speed = 6 + (seed % 16)
        pressure = 1002 + (seed % 20)
        conditions = ["sunny", "partly cloudy", "cloudy", "rainy"]
        description = conditions[seed % len(conditions)]
        return {
            "temperature": temperature,
            "humidity": humidity,
            "pressure": pressure,
            "wind_speed": wind_speed,
            "description": description,
            "visibility": 10,
            "location": f"{city}, {state}"
        }
    
    def _get_mock_forecast_data(self, city: str, state: str) -> Dict[str, Any]:
        """Mock forecast data for development, varied by location."""
        seed = self._loc_seed(city, state)
        base_temp = 18 + (seed % 12)
        conditions = ["sunny", "cloudy", "rainy", "partly cloudy"]
        today = datetime.utcnow().date()

        forecast = []
        for offset in range(3):
            day = today + timedelta(days=offset)
            forecast.append({
                "date": f"{day.isoformat()} 12:00:00",
                "temperature": base_temp + (offset % 3) - 1,
                "humidity": 50 + ((seed + offset * 7) % 30),
                "description": conditions[(seed + offset) % len(conditions)]
            })

        return {
            "forecast": forecast,
            "location": f"{city}, {state}"
        }

# Initialize weather service
weather_service = WeatherService()
