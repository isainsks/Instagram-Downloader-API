from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers.media import router as media_router
from app.schemas import HealthResponse


app = FastAPI(
    title="Instagram Media Downloader API",
    description="Returns Instagram image and video metadata with direct media links.",
    version="3.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(get_settings().allowed_origins),
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.include_router(media_router)


@app.get("/", tags=["System"])
async def root() -> dict:
    settings = get_settings()
    return {
        "name": app.title,
        "version": app.version,
        "docs": "/docs",
        "endpoints": {
            "media": "/api/media?url=INSTAGRAM_URL",
            "video": "/api/video?url=INSTAGRAM_URL",
            "download": "/api/download?url=INSTAGRAM_URL",
        },
        "security": {
            "api_key_required": settings.api_key_required,
            "rate_limit_enabled": settings.rate_limit_enabled,
        },
    }


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
