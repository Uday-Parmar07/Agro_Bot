import os
import tempfile
import uuid

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.gettempdir()}/agrobot_security_test_{uuid.uuid4().hex}.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import httpx
from starlette.requests import Request

from app.main import app
from app.routers.disease import MAX_IMAGE_BYTES
from app.utils import rate_limit
from app.utils.rate_limit import client_ip, limiter


def _request(headers: dict) -> Request:
    return Request({
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": ("10.0.0.5", 1234),
    })


def test_client_ip_uses_address_appended_by_load_balancer():
    assert client_ip(_request({"X-Forwarded-For": "1.2.3.4, 203.0.113.9"})) == "203.0.113.9"
    assert client_ip(_request({})) == "10.0.0.5"


def test_client_ip_skips_trusted_proxy_hops(monkeypatch):
    # Cloudflare appends the client, then the ALB appends the Cloudflare edge.
    monkeypatch.setattr(rate_limit, "TRUSTED_PROXY_HOPS", 2)
    headers = {"X-Forwarded-For": "6.6.6.6, 198.51.100.7, 172.70.1.1"}
    assert client_ip(_request(headers)) == "198.51.100.7"
    assert client_ip(_request({"X-Forwarded-For": "198.51.100.7"})) == "198.51.100.7"


async def test_security_limits():
    transport = httpx.ASGITransport(app=app)
    limiter.reset()
    async with app.router.lifespan_context(app):
        try:
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                for path in ("/docs", "/openapi.json"):
                    response = await client.get(path)
                    assert response.status_code == 404, path

                short = await client.post(
                    "/api/auth/signup",
                    json={"email": "short@example.com", "password": "short", "full_name": "Short"},
                )
                assert short.status_code == 422

                signup = await client.post(
                    "/api/auth/signup",
                    json={"email": "limits@example.com", "password": "long-enough", "full_name": "Limits"},
                )
                signup.raise_for_status()
                headers = {"Authorization": f"Bearer {signup.json()['access_token']}"}

                too_big = await client.post(
                    "/api/disease/predict",
                    files={"image": ("leaf.png", b"\0" * (MAX_IMAGE_BYTES + 1), "image/png")},
                    headers=headers,
                )
                assert too_big.status_code == 413

                not_an_image = await client.post(
                    "/api/disease/predict",
                    files={"image": ("leaf.png", b"not really a png", "image/png")},
                    headers=headers,
                )
                assert not_an_image.status_code == 400

                statuses = []
                for _ in range(11):
                    login = await client.post(
                        "/api/auth/login",
                        data={"username": "limits@example.com", "password": "wrong-password"},
                    )
                    statuses.append(login.status_code)
                assert statuses[:10] == [401] * 10
                assert statuses[10] == 429
                assert isinstance(login.json()["detail"], str)
        finally:
            limiter.reset()
