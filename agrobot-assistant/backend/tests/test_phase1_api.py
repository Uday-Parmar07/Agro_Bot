import base64
import asyncio
import os
import tempfile
import uuid

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.gettempdir()}/agrobot_phase1_api_test_{uuid.uuid4().hex}.db"
os.environ.setdefault("GROQ_API_KEY", "test-key")
os.environ.setdefault("TAVILY_API_KEY", "test-key")
os.environ.setdefault("SECRET_KEY", "test-secret")

import httpx

from app.main import app


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


async def _auth_headers(client: httpx.AsyncClient):
    email = "phase1@example.com"
    signup = await client.post(
        "/api/auth/signup",
        json={
            "email": email,
            "password": "phase1-password",
            "full_name": "Phase One Farmer",
            "phone_number": "9999999999",
        },
    )
    if signup.status_code == 400:
        login = await client.post(
            "/api/auth/login",
            data={"username": email, "password": "phase1-password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        login.raise_for_status()
        token = login.json()["access_token"]
    else:
        signup.raise_for_status()
        token = signup.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _complete_questionnaire(client: httpx.AsyncClient, headers: dict):
    me = await client.get("/api/auth/me", headers=headers)
    me.raise_for_status()
    user_id = me.json()["id"]

    response = await client.post(
        "/api/questionnaire/complete",
        json={
            "user_id": user_id,
            "soil_physical": {
                "soil_texture": "loamy",
                "water_retention": "moderate",
                "soil_top_layer": "dark_crumbly",
            },
            "soil_fertility": {
                "soil_test_done": True,
                "npk_nitrogen": 50,
                "npk_phosphorus": 40,
                "npk_potassium": 35,
                "soil_ph": 6.8,
                "yellowing_slow_growth": False,
                "fertilizer_type": "organic",
            },
            "moisture_irrigation": {
                "irrigation_type": "drip",
                "watering_frequency": "weekly",
            },
            "environmental": {
                "state": "Maharashtra",
                "district": "Pune",
                "average_rainfall": 700,
                "average_temperature": 27,
                "total_area": 4,
                "area_unit": "acre",
            },
            "organic_practices": {
                "uses_organic_matter": True,
                "organic_matter_types": ["compost"],
                "crop_residue_practice": "leave_in_field",
                "earthworms_present": True,
            },
        },
        headers=headers,
    )
    response.raise_for_status()


async def test_phase1_endpoints():
    transport = httpx.ASGITransport(app=app)
    await app.router.startup()
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            headers = await _auth_headers(client)
            await _complete_questionnaire(client, headers)

            farms = await client.get("/api/farms", headers=headers)
            farms.raise_for_status()
            farm_id = farms.json()[0]["id"]

            created_crop = await client.post(
                "/api/dashboard/crops",
                json={
                    "farm_id": farm_id,
                    "crop_name": "Tomato",
                    "variety": "Arka Rakshak",
                    "area_acres": 1.5,
                    "planting_date": "2026-08-01",
                    "expected_harvest_date": "2026-11-01",
                },
                headers=headers,
            )
            created_crop.raise_for_status()
            crop_id = created_crop.json()["id"]

            crops = await client.get(f"/api/dashboard/crops?farm_id={farm_id}", headers=headers)
            crops.raise_for_status()
            assert any(crop["id"] == crop_id for crop in crops.json())

            weather = await client.get(f"/api/weather/overview?farm_id={farm_id}", headers=headers)
            weather.raise_for_status()
            assert "current" in weather.json()

            disease = await client.post(
                f"/api/disease/predict?farm_id={farm_id}",
                files={"image": ("leaf.png", PNG_1X1, "image/png")},
                headers=headers,
            )
            disease.raise_for_status()
            assert "predicted_class" in disease.json()

            disease_history = await client.get(f"/api/disease/history?farm_id={farm_id}", headers=headers)
            disease_history.raise_for_status()
            assert len(disease_history.json()) >= 1

            analytics = await client.get(f"/api/analytics/overview?farm_id={farm_id}", headers=headers)
            analytics.raise_for_status()
            assert analytics.json()["farm_id"] == farm_id

            removed = await client.delete(f"/api/dashboard/crops/{crop_id}", headers=headers)
            removed.raise_for_status()
    finally:
        await app.router.shutdown()


if __name__ == "__main__":
    asyncio.run(test_phase1_endpoints())
    print("Phase 1 API smoke test passed")
