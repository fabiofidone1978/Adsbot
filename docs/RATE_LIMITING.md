**Rate Limiting**

- **Purpose**: protect ChatGPT API usage for `user` profile by blocking after a small number of requests.
- **Policy implemented**: Redis fixed-window blocking. After N requests in a `window_seconds` interval, the key is blocked for one full window (429 + Retry-After). `admin` keys are exempt.

Configuration
- `REDIS_URL` (optional): Redis connection URL, e.g. `redis://localhost:6379/0`. If not provided, the rate limiter will attempt to connect to `redis://localhost:6379/0` by default.
- `ADMIN_API_KEYS`, `USER_API_KEYS`: comma-separated lists set in `.env`.

How it works
- Each request with an API key increments a window-specific counter `rl:{api_key}:count:{window_start}`.
- When counter exceeds the configured `max_requests`, a `rl:{api_key}:blocked` key is set with an expiry equal to the window length.
- Subsequent requests receive HTTP 429 with `Retry-After` header until block expires.

FastAPI integration
- Add to FastAPI app:

```py
from adsbot.rate_limiter import RedisRateLimiter
from adsbot.middleware_fastapi import RateLimitMiddleware

limiter = RedisRateLimiter(window_seconds=60, max_requests=5)
app.add_middleware(RateLimitMiddleware, limiter=limiter)
```

Testing
- Unit tests are provided in `tests/test_rate_limiter.py`. They use an in-memory fake Redis implementation so they run without a real Redis server.
