import os
from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse
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

BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_BUILD_DIR = BASE_DIR / "frontend" / "build"
FRONTEND_INDEX = FRONTEND_BUILD_DIR / "index.html"

@app.on_event("startup")
async def startup_event():
    create_tables()

@app.get("/")
async def root():
    if FRONTEND_INDEX.exists():
        return FileResponse(FRONTEND_INDEX)
    return {"message": "AgroBot API is running!"}


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):

    if full_path.startswith("api/") or full_path == "api":
        return {"detail": "Not Found"}

    requested_file = (FRONTEND_BUILD_DIR / full_path).resolve()
    if FRONTEND_BUILD_DIR.exists() and requested_file.is_file():
        try:
            requested_file.relative_to(FRONTEND_BUILD_DIR)
        except ValueError:
            return {"detail": "Not Found"}
        return FileResponse(requested_file)

    if FRONTEND_INDEX.exists():
        return FileResponse(FRONTEND_INDEX)

    return {"detail": "Frontend build not found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
