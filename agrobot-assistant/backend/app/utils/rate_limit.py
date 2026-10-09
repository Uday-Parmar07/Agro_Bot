import os

from fastapi import Request
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from app.utils.auth_utils import ALGORITHM, SECRET_KEY


def client_ip(request: Request) -> str:
    # Behind the ALB the right-most X-Forwarded-For entry is the address the
    # ALB itself saw; anything to its left is client-supplied and spoofable.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
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
