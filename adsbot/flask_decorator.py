"""Synchronous Flask decorator wrapper for the async rate limiter.

Usage:

from adsbot.rate_limiter import RedisRateLimiter
from adsbot.flask_decorator import rate_limit

limiter = RedisRateLimiter(window_seconds=60, max_requests=5)

@app.route('/my-endpoint')
@rate_limit(limiter)
def my_endpoint():
    return 'ok'
"""

from functools import wraps
import asyncio
from typing import Callable

from adsbot import api_keys


def rate_limit(limiter):
    """Return a Flask-compatible decorator that enforces rate limits.

    `limiter` must expose an async method `increment_and_check(api_key)` that
    returns (allowed: bool, remaining: int, retry_after_or_none: Optional[int]).
    """

    def decorator(f: Callable):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Flask exposes request in globals; import here to avoid top-level dependency
            from flask import request, jsonify

            api_key = request.headers.get("X-API-Key") or request.args.get("api_key")
            role = api_keys.get_role(api_key) if api_key else None
            if role == "admin":
                return f(*args, **kwargs)
            if role != "user":
                # Unknown key: let the endpoint handle authentication, or reject here
                return f(*args, **kwargs)

            # Call the async limiter from sync context
            try:
                allowed, remaining, retry_after = asyncio.run(limiter.increment_and_check(api_key))
            except Exception as e:
                # If limiter fails, allow by default to avoid denying service
                return f(*args, **kwargs)

            if not allowed:
                resp = jsonify({"detail": "Rate limit exceeded", "retry_after": retry_after})
                resp.status_code = 429
                resp.headers["Retry-After"] = str(retry_after)
                return resp

            # Apply slowdown if present (sleep before responding)
            # Note: slowdown is applied by the async limiter; Flask caller sees delay in response time
            return f(*args, **kwargs)

        return wrapper

    return decorator
