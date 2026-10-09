import os

from fastapi import Request
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from app.utils.auth_utils import ALGORITHM, SECRET_KEY


# How many proxies in front of the app append to X-Forwarded-For. Each one
# appends the address it received the request from, so the entry this many
# places from the right is the real client; anything further left is
# client-supplied and spoofable. Production is Cloudflare -> ALB, so 2.
TRUSTED_PROXY_HOPS = max(1, int(os.getenv("TRUSTED_PROXY_HOPS", "1")))


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
        if hops:
            return hops[-min(TRUSTED_PROXY_HOPS, len(hops))]
    return request.client.host if request.client else "unknown"


def user_or_ip(request: Request) -> str:
    """Key authenticated endpoints per account, so users sharing a carrier NAT
    don't exhaust each other's quota. Signature is checked; expiry is not, since
    the auth dependency has already rejected expired tokens."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            payload = jwt.decode(
                auth[7:], SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False}
            )
            if payload.get("sub"):
                return f"user:{payload['sub']}"
        except JWTError:
            pass
    return f"ip:{client_ip(request)}"


# In-memory counters are per process. With several ECS tasks the effective
# limit is multiplied by the task count; set RATE_LIMIT_STORAGE_URI to a shared
# store (e.g. redis://...) to make limits global.
limiter = Limiter(
    key_func=client_ip,
    storage_uri=os.getenv("RATE_LIMIT_STORAGE_URI", "memory://"),
    enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower() in {"1", "true", "yes"},
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please wait a minute and try again."},
        headers={"Retry-After": "60"},
    )
