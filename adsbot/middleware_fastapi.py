"""ASGI middleware for FastAPI that enforces API key rate limits.

Usage: add `app.add_middleware(RateLimitMiddleware, limiter=limiter)` where
`limiter` is an instance of `RedisRateLimiter` from `adsbot.rate_limiter`.
"""

from __future__ import annotations

import json
from typing import Callable, Optional

from starlette.types import ASGIApp, Receive, Scope, Send

from adsbot import api_keys
from .rate_limiter import RedisRateLimiter
import asyncio


class RateLimitMiddleware:
    def __init__(self, app: ASGIApp, *, limiter: RedisRateLimiter):
        self.app = app
        self.limiter = limiter

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Only handle HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}

        # Extract API key from header or querystring
        api_key = headers.get("x-api-key")
        if not api_key:
            # try querystring
            qs = scope.get("query_string", b"").decode()
            for part in qs.split("&"):
                if part.startswith("api_key="):
                    api_key = part.split("=", 1)[1]
                    break

        role = api_keys.get_role(api_key) if api_key else None
        # Admins are exempt
        if role == "admin":
            await self.app(scope, receive, send)
            return

        # If unknown key, treat as unauthenticated and pass through (or could reject)
        if role != "user":
            await self.app(scope, receive, send)
            return

        # Rate limit users
        allowed, remaining, retry_after, slowdown = await self.limiter.increment_and_check(api_key)
        if not allowed:
            # Return 429
            headers_out = [(b"content-type", b"application/json"), (b"retry-after", str(retry_after).encode())]

            body = json.dumps({"detail": "Rate limit exceeded", "retry_after": retry_after}).encode()

            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": headers_out,
            })
            await send({"type": "http.response.body", "body": body})
            return

        # If slowdown mode returned a delay, apply it before continuing
        if slowdown:
            try:
                await asyncio.sleep(float(slowdown))
            except Exception:
                pass

        # Add remaining and slowdown header and continue
        async def send_wrapper(message):
            # inject header on response start
            if message["type"] == "http.response.start":
                headers = list(message.setdefault("headers", []))
                headers.append((b"x-rate-limit-remaining", str(remaining).encode()))
                if slowdown:
                    headers.append((b"x-rate-limit-slowdown", str(slowdown).encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


__all__ = ["RateLimitMiddleware"]
