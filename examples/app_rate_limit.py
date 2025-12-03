"""Minimal FastAPI example showing rate limit middleware in action.

Run with:
    pip install -r requirements.txt
    uvicorn examples.app_rate_limit:app --reload --port 8000

Then test:
    curl -H "X-API-Key: sk-user-example-1" http://127.0.0.1:8000/test
"""

from fastapi import FastAPI
from adsbot.rate_limiter import RedisRateLimiter
from adsbot.middleware_fastapi import RateLimitMiddleware

app = FastAPI()

# configure limiter (will attempt to connect to REDIS_URL or localhost)
limiter = RedisRateLimiter(window_seconds=60, max_requests=5)
app.add_middleware(RateLimitMiddleware, limiter=limiter)


@app.get("/test")
async def test_endpoint():
    return {"status": "ok"}
