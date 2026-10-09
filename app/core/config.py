import os
from dataclasses import dataclass
from functools import lru_cache


def _csv(name: str) -> tuple[str, ...]:
    return tuple(value.strip() for value in os.getenv(name, "").split(",") if value.strip())


def _integer(name: str, default: int, minimum: int = 0) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        return max(int(raw_value), minimum)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    allowed_origins: tuple[str, ...]
    api_keys: tuple[str, ...]
    rate_limit_requests: int
    rate_limit_window_seconds: int
    instagram_proxies: tuple[str, ...]
    instagram_http_proxy: str | None
    instagram_https_proxy: str | None
    instagram_request_timeout: int

    @property
    def api_key_required(self) -> bool:
        return bool(self.api_keys)

    @property
    def rate_limit_enabled(self) -> bool:
        return self.rate_limit_requests > 0


@lru_cache
def get_settings() -> Settings:
    api_keys = _csv("API_KEYS")
    legacy_api_key = os.getenv("API_KEY", "").strip()
    if legacy_api_key and legacy_api_key not in api_keys:
        api_keys += (legacy_api_key,)

    proxies = _csv("INSTAGRAM_PROXIES")
    single_proxy = os.getenv("INSTAGRAM_PROXY", "").strip()
    if single_proxy and single_proxy not in proxies:
        proxies += (single_proxy,)

    return Settings(
        allowed_origins=_csv("ALLOWED_ORIGINS") or ("*",),
        api_keys=api_keys,
        rate_limit_requests=_integer("RATE_LIMIT_REQUESTS", 60),
        rate_limit_window_seconds=_integer("RATE_LIMIT_WINDOW_SECONDS", 60, minimum=1),
        instagram_proxies=proxies,
        instagram_http_proxy=os.getenv("INSTAGRAM_HTTP_PROXY") or None,
        instagram_https_proxy=os.getenv("INSTAGRAM_HTTPS_PROXY") or None,
        instagram_request_timeout=_integer(
            "INSTAGRAM_REQUEST_TIMEOUT", 30, minimum=1
        ),
    )
