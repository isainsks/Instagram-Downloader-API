import re
import threading
from typing import Any
from urllib.parse import urlsplit

from app.core.config import get_settings

try:
    import instaloader
except ImportError:
    instaloader = None


INSTAGRAM_URL_PATTERN = re.compile(
    r"^(?:https?://)?(?:www\.)?instagram\.com/"
    r"(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)(?:[/?#]|$)",
    flags=re.IGNORECASE,
)
SUPPORTED_PROXY_SCHEMES = {
    "http",
    "https",
    "socks4",
    "socks4a",
    "socks5",
    "socks5h",
}
_proxy_lock = threading.Lock()
_proxy_index = 0


class InstagramServiceError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def extract_shortcode(url: str) -> str | None:
    if not isinstance(url, str):
        return None

    match = INSTAGRAM_URL_PATTERN.search(url.strip())
    return match.group(1) if match else None


def _safe_value(post: Any, attribute: str, default: Any = None) -> Any:
    try:
        return getattr(post, attribute)
    except Exception:
        return default


def _validate_proxy_url(proxy_url: str) -> str:
    parsed = urlsplit(proxy_url)
    if parsed.scheme.lower() not in SUPPORTED_PROXY_SCHEMES or not parsed.hostname:
        raise InstagramServiceError(
            "Invalid proxy configuration. Use an HTTP, HTTPS, SOCKS4, or SOCKS5 URL.",
            status_code=500,
        )
    return proxy_url


def _next_proxy() -> str | None:
    global _proxy_index

    proxies = get_settings().instagram_proxies
    if not proxies:
        return None

    with _proxy_lock:
        proxy_url = proxies[_proxy_index % len(proxies)]
        _proxy_index += 1
    return _validate_proxy_url(proxy_url)


def _configure_proxy(loader: Any) -> None:
    settings = get_settings()
    shared_proxy = _next_proxy()
    proxies: dict[str, str] = {}

    if shared_proxy:
        proxies.update({"http": shared_proxy, "https": shared_proxy})
    if settings.instagram_http_proxy:
        proxies["http"] = _validate_proxy_url(settings.instagram_http_proxy)
    if settings.instagram_https_proxy:
        proxies["https"] = _validate_proxy_url(settings.instagram_https_proxy)

    if proxies:
        loader.context._session.proxies.update(proxies)


def get_media_info(url: str) -> dict[str, Any]:
    shortcode = extract_shortcode(url)
    if not shortcode:
        raise InstagramServiceError(
            "Invalid URL. Use an Instagram post, reel, or IGTV URL.",
            status_code=422,
        )

    if instaloader is None:
        raise InstagramServiceError(
            "Instaloader is not installed.",
            status_code=503,
        )

    settings = get_settings()
    loader = instaloader.Instaloader(
        quiet=True,
        request_timeout=settings.instagram_request_timeout,
    )
    _configure_proxy(loader)

    try:
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        media = []

        if post.typename == "GraphSidecar":
            for index, node in enumerate(post.get_sidecar_nodes(), start=1):
                if node.is_video and node.video_url:
                    media.append(
                        {
                            "index": index,
                            "type": "video",
                            "download_url": node.video_url,
                            "thumbnail_url": node.display_url,
                        }
                    )
                elif not node.is_video and node.display_url:
                    media.append(
                        {
                            "index": index,
                            "type": "image",
                            "download_url": node.display_url,
                            "thumbnail_url": node.display_url,
                        }
                    )
        elif post.is_video and post.video_url:
            media.append(
                {
                    "index": 1,
                    "type": "video",
                    "download_url": post.video_url,
                    "thumbnail_url": post.url,
                }
            )
        elif post.url:
            media.append(
                {
                    "index": 1,
                    "type": "image",
                    "download_url": post.url,
                    "thumbnail_url": post.url,
                }
            )

        if not media:
            raise InstagramServiceError(
                "The post does not contain downloadable media.",
                status_code=404,
            )

        images = [item for item in media if item["type"] == "image"]
        videos = [item for item in media if item["type"] == "video"]

        published_at = _safe_value(post, "date_utc")
        published_at = published_at.isoformat() if published_at else None

        return {
            "shortcode": post.shortcode,
            "instagram_url": f"https://www.instagram.com/p/{post.shortcode}/",
            "media_type": post.typename,
            "owner": _safe_value(post, "owner_username"),
            "caption": _safe_value(post, "caption"),
            "published_at": published_at,
            "likes": _safe_value(post, "likes"),
            "comments": _safe_value(post, "comments"),
            "media_count": len(media),
            "image_count": len(images),
            "video_count": len(videos),
            "duration_seconds": _safe_value(post, "video_duration"),
            "view_count": _safe_value(post, "video_view_count"),
            "play_count": _safe_value(post, "video_play_count"),
            "thumbnail_url": _safe_value(post, "url"),
            "download_url": media[0]["download_url"],
            "media": media,
            "images": images,
            "videos": videos,
        }
    except InstagramServiceError:
        raise
    except instaloader.exceptions.LoginRequiredException as error:
        raise InstagramServiceError(
            "This content requires an Instagram login.",
            status_code=403,
        ) from error
    except instaloader.exceptions.PrivateProfileNotFollowedException as error:
        raise InstagramServiceError(
            "The Instagram profile is private.",
            status_code=403,
        ) from error
    except instaloader.exceptions.QueryReturnedNotFoundException as error:
        raise InstagramServiceError(
            "The post does not exist or is unavailable.",
            status_code=404,
        ) from error
    except Exception as error:
        raise InstagramServiceError(
            f"Instagram could not process the request: {error}",
            status_code=502,
        ) from error
