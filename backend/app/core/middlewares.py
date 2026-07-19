import json
from datetime import datetime, timedelta
import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
from app.core.database import async_session_factory
from app.repositories.idempotency import IdempotencyRepository

logger = structlog.get_logger()

# Simple In-Memory Rate Limiter fallback for simplicity and durability
RATE_LIMIT_STORE = {}

class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Only validate write operations
        if request.method not in ["POST", "PATCH", "PUT"]:
            return await call_next(request)

        # Exclude authentication tokens
        if "/auth/token" in request.url.path:
            return await call_next(request)

        idempotency_key = request.headers.get("X-Idempotency-Key")
        if not idempotency_key:
            return await call_next(request)

        # We need a db session to check and write idempotency keys
        async with async_session_factory() as session:
            repo = IdempotencyRepository(session)
            
            # 1. Lookup key in database
            existing_key = await repo.get_by_key(idempotency_key)
            if existing_key:
                logger.info(
                    "Idempotent Request Intercepted",
                    key=idempotency_key,
                    path=request.url.path
                )
                # Return the cached response
                return StarletteResponse(
                    content=json.dumps(existing_key.response_body),
                    status_code=existing_key.response_status,
                    media_type="application/json"
                )

            # Proceed with the request
            response: Response = await call_next(request)

            # Only cache 2xx and 4xx client errors (don't cache 5xx server issues)
            if 200 <= response.status_code < 500:
                # Capture response body
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk

                try:
                    body_json = json.loads(response_body.decode("utf-8"))
                    await repo.create_key(
                        key=idempotency_key,
                        response_status=response.status_code,
                        response_body=body_json
                    )
                    await session.commit()
                except Exception as e:
                    logger.error("Failed to store idempotency key", error=str(e))

                # Reconstruct the response since we consumed its body iterator
                return StarletteResponse(
                    content=response_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
            
            return response


class RateLimitingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = datetime.utcnow()
        
        # Simple token bucket limit: 60 requests per minute per IP
        if client_ip not in RATE_LIMIT_STORE:
            RATE_LIMIT_STORE[client_ip] = []
            
        timestamps = RATE_LIMIT_STORE[client_ip]
        # Keep only timestamps from the last 60 seconds
        timestamps = [t for t in timestamps if now - t < timedelta(seconds=60)]
        RATE_LIMIT_STORE[client_ip] = timestamps
        
        if len(timestamps) >= 60:
            logger.warn("Rate Limit Exceeded", client_ip=client_ip, path=request.url.path)
            return StarletteResponse(
                content=json.dumps({"detail": "Too many requests. Rate limit is 60 requests per minute."}),
                status_code=429,
                media_type="application/json"
            )
            
        timestamps.append(now)
        return await call_next(request)
