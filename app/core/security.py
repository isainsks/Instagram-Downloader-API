import hashlib
import secrets

from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import APIKeyHeader

from app.core.config import get_settings
from app.core.rate_limit import FixedWindowRateLimiter


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
rate_limiter = FixedWindowRateLimiter()


def _authenticate(api_key: str | None) -> str | None:
    settings = get_settings()
    if not settings.api_key_required:
        return None

    if not api_key or not any(
        secrets.compare_digest(api_key, configured_key)
        for configured_key in settings.api_keys
    ):
        raise HTTPException(
            status_code=401,
            detail="A valid API key is required.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key


async def enforce_api_access(
    request: Request,
    response: Response,
    api_key: str | None = Depends(api_key_header),
) -> None:
    settings = get_settings()
    authenticated_key = _authenticate(api_key)

    if not settings.rate_limit_enabled:
        return

    if authenticated_key:
        digest = hashlib.sha256(authenticated_key.encode("utf-8")).hexdigest()
        identity = f"key:{digest}"
    else:
        client_host = request.client.host if request.client else "unknown"
        identity = f"ip:{client_host}"

    remaining, retry_after = rate_limiter.check(
        identity,
        settings.rate_limit_requests,
        settings.rate_limit_window_seconds,
    )
    headers = {
        "X-RateLimit-Limit": str(settings.rate_limit_requests),
        "X-RateLimit-Remaining": str(max(0, remaining)),
        "X-RateLimit-Window": str(settings.rate_limit_window_seconds),
    }

    if remaining < 0:
        headers["Retry-After"] = str(retry_after)
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again later.",
            headers=headers,
        )

    for name, value in headers.items():
        response.headers[name] = value
