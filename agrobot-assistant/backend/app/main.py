import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, questionnaire, recommendations, disease, weather
from app.database.connection import create_tables

app = FastAPI(
    title="AgroBot API",
    description="AI-powered agricultural assistant backend",
    version="1.0.0"
)

# CORS middleware for frontend
cors_origins = os.getenv("CORS_ORIGINS", "").strip()
allow_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin"],
    max_age=86400,
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(questionnaire.router, prefix="/api/questionnaire", tags=["Questionnaire"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["AI Recommendations"])
app.include_router(disease.router, prefix="/api/disease", tags=["Disease Checkup"])
app.include_router(weather.router, prefix="/api/weather", tags=["Weather"])

@app.on_event("startup")
async def startup_event():
    create_tables()

@app.get("/")
async def root():
    return {"message": "AgroBot API is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
