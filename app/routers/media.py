from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from app.schemas import MediaResponse
from app.core.security import enforce_api_access
from app.services.instagram import InstagramServiceError, get_media_info


router = APIRouter(
    prefix="/api",
    tags=["Media"],
    dependencies=[Depends(enforce_api_access)],
)


async def _resolve_media(url: str) -> MediaResponse:
    try:
        data = await run_in_threadpool(get_media_info, url)
    except InstagramServiceError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail=error.message,
        ) from error

    return MediaResponse(data=data)


@router.get("/media", response_model=MediaResponse)
async def media_info(
    url: str = Query(..., description="Public Instagram post, reel, or IGTV URL"),
) -> MediaResponse:
    """Return metadata and direct links for images and videos."""
    return await _resolve_media(url)


@router.get("/video", response_model=MediaResponse)
async def video_info(
    url: str = Query(..., description="Public Instagram post, reel, or IGTV URL"),
) -> MediaResponse:
    """Backward-compatible alias that returns all post media."""
    return await _resolve_media(url)


@router.get("/download", response_model=MediaResponse)
async def download_info(
    url: str = Query(..., description="Public Instagram post, reel, or IGTV URL"),
) -> MediaResponse:
    """GET alias that returns all download information."""
    return await _resolve_media(url)
