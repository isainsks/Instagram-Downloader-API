# Instagram Media Downloader API

A FastAPI service that uses Instaloader to return metadata and direct download
links for images and videos from public Instagram posts, reels, and IGTV posts.
It does not store media files.

## Project structure

```text
app/
├── core/
│   ├── config.py           # Environment-based settings
│   ├── rate_limit.py       # Thread-safe rate limiter
│   └── security.py         # API key authentication
├── routers/
│   └── media.py            # GET endpoints
├── services/
│   └── instagram.py        # Instaloader and proxy integration
├── main.py                 # FastAPI application and CORS
└── schemas.py              # Response models
Dockerfile
compose.yaml
requirements.txt
```

## Endpoints

```text
GET /health
GET /api/media?url=INSTAGRAM_URL
GET /api/video?url=INSTAGRAM_URL
GET /api/download?url=INSTAGRAM_URL
GET /docs
```

The three media endpoints return the same response. `download_url` contains the
first direct link, `media` preserves the original post order, and `images` and
`videos` provide filtered lists.

## API key authentication

Set one or more keys in the environment. Authentication is disabled when both
variables are empty.

```env
API_KEY=one-key
API_KEYS=first-key,second-key
```

Clients must send a configured key in the `X-API-Key` header:

```powershell
curl.exe -G "http://localhost:8000/api/media" `
  -H "X-API-Key: first-key" `
  --data-urlencode "url=https://www.instagram.com/p/SHORTCODE/"
```

Missing or invalid credentials receive `401 Unauthorized`. Keep production keys
in the hosting provider's secret manager rather than committing them to Git.
The interactive documentation provides an **Authorize** button that stores the
key and sends it as `X-API-Key` when testing protected endpoints.

## Rate limiting

The limit applies to media endpoints and is tracked by API key when
authentication is enabled, or by client IP otherwise.

```env
RATE_LIMIT_REQUESTS=60
RATE_LIMIT_WINDOW_SECONDS=60
```

Set `RATE_LIMIT_REQUESTS=0` to disable it. Responses include
`X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Window`. Exceeded
limits return `429 Too Many Requests` with `Retry-After`.

The built-in limiter is stored in each application process. For a strict shared
limit across multiple replicas, enforce the limit at the hosting gateway or use
a shared Redis-backed limiter.

## Proxy support

Supported proxy URL schemes are `http://`, `https://`, `socks4://`,
`socks4a://`, `socks5://`, and `socks5h://`. Credentials can be embedded in the
URL and must be percent-encoded when they contain reserved characters.

Use a single proxy:

```env
INSTAGRAM_PROXY=socks5h://username:password@proxy.example:1080
```

Use a round-robin proxy pool:

```env
INSTAGRAM_PROXIES=http://proxy-one.example:8080,socks5h://proxy-two.example:1080
```

Use protocol-specific overrides:

```env
INSTAGRAM_HTTP_PROXY=http://proxy.example:8080
INSTAGRAM_HTTPS_PROXY=socks5h://proxy.example:1080
```

`INSTAGRAM_HTTP_PROXY` and `INSTAGRAM_HTTPS_PROXY` override the corresponding
protocol from `INSTAGRAM_PROXY` or the selected pool entry. Proxy configuration
is server-side only and is never accepted from an API request.

The upstream request timeout can also be changed:

```env
INSTAGRAM_REQUEST_TIMEOUT=30
```

## Local development

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Interactive API documentation is available at `http://localhost:8000/docs`.

## Docker

Copy the example configuration and set secure values:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

Or build and run the image directly:

```powershell
docker build -t instagram-media-api .
docker run --rm -p 8000:8000 `
  -e API_KEYS="replace-with-a-long-random-key" `
  -e RATE_LIMIT_REQUESTS="60" `
  -e ALLOWED_ORIGINS="https://your-frontend.example" `
  instagram-media-api
```

## Web deployment

The root `Dockerfile` can be deployed by services such as Render, Railway,
Fly.io, and other container platforms:

1. Push this directory to a Git repository.
2. Create a Docker-based web service from the repository.
3. Configure `/health` as the healthcheck path.
4. Store `API_KEYS`, proxy credentials, and other configuration as secrets.
5. Set `ALLOWED_ORIGINS` to the frontend domains, separated by commas.
6. Let the platform provide `PORT`; the default is `8000`.

## Environment variables

| Variable | Default | Description |
|---|---:|---|
| `PORT` | `8000` | HTTP listening port |
| `ALLOWED_ORIGINS` | `*` | Comma-separated CORS origins |
| `API_KEY` | empty | Single accepted API key |
| `API_KEYS` | empty | Comma-separated accepted API keys |
| `RATE_LIMIT_REQUESTS` | `60` | Requests allowed per window; `0` disables |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate-limit window length |
| `INSTAGRAM_PROXY` | empty | Single proxy for all Instagram traffic |
| `INSTAGRAM_PROXIES` | empty | Comma-separated round-robin proxy pool |
| `INSTAGRAM_HTTP_PROXY` | empty | HTTP-specific proxy override |
| `INSTAGRAM_HTTPS_PROXY` | empty | HTTPS-specific proxy override |
| `INSTAGRAM_REQUEST_TIMEOUT` | `30` | Upstream timeout in seconds |
| `FORWARDED_ALLOW_IPS` | `*` | Reverse proxies trusted by Uvicorn |
