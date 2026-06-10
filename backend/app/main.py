from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.v1.router import router as v1_router
from backend.app.api.planets import router as planets_router
from backend.app.api.cycle import router as cycle_router
from backend.app.api.composite import router as composite_router
from backend.app.api.scanner import router as scanner_router
from backend.app.api.turning_points import router as turning_points_router
from backend.app.api.analyst import router as analyst_router
from backend.app.api.predictions import router as predictions_router
from backend.app.api.context import router as context_router
from backend.app.api.ohlcv import router as ohlcv_router
from backend.app.api.kie_media import router as kie_media_router
from backend.app.api.dsi_radar import router as dsi_radar_router
from backend.app.core.config import settings

frontend_origins = [origin.strip() for origin in settings.FRONTEND_URL.split(",") if origin.strip()]

app = FastAPI(
    title="AstroCycle API",
    version="1.0.0",
    description="AstroCycle backend untuk SaaS cycle forecasting.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for split architecture
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/v1")
app.include_router(planets_router, prefix="/api")
app.include_router(cycle_router, prefix="/api")
app.include_router(composite_router, prefix="/api")
app.include_router(scanner_router, prefix="/api")
app.include_router(turning_points_router, prefix="/api")
app.include_router(analyst_router, prefix="/api")
app.include_router(predictions_router, prefix="/api")
app.include_router(context_router, prefix="/api")
app.include_router(ohlcv_router, prefix="/api")
app.include_router(kie_media_router, prefix="/api")
app.include_router(dsi_radar_router, prefix="/api")


@app.get("/")
def root():
    return {
        "name": "AstroCycle API",
        "status": "online",
        "health": "/health",
        "docs": "/docs",
        "api_prefixes": ["/api", "/v1"],
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}