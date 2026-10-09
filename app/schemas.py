from typing import Literal

from pydantic import BaseModel


class MediaLink(BaseModel):
    index: int
    type: Literal["image", "video"]
    download_url: str
    thumbnail_url: str | None = None


class MediaData(BaseModel):
    shortcode: str
    instagram_url: str
    media_type: str
    owner: str | None = None
    caption: str | None = None
    published_at: str | None = None
    likes: int | None = None
    comments: int | None = None
    media_count: int = 1
    image_count: int
    video_count: int
    duration_seconds: float | None = None
    view_count: int | None = None
    play_count: int | None = None
    thumbnail_url: str | None = None
    download_url: str
    media: list[MediaLink]
    images: list[MediaLink]
    videos: list[MediaLink]


class MediaResponse(BaseModel):
    success: bool = True
    data: MediaData
    notice: str = "Direct Instagram media links may expire."


class HealthResponse(BaseModel):
    status: str
