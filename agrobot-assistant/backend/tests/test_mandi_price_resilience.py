import unittest
from unittest.mock import patch

import httpx

from app.services.mandi_price_service import MandiPriceService


class _FailingClient:
    def __init__(self):
        self.calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def get(self, *_args, **_kwargs):
        self.calls += 1
        raise httpx.ReadTimeout("timed out")


class MandiPriceResilienceTests(unittest.IsolatedAsyncioTestCase):
    async def test_api_failure_opens_circuit_and_logs_once(self):
        service = MandiPriceService()
        service.api_key = "test-key"
        service.enable_curl_fallback = False
        service.failure_backoff_seconds = 60
        client = _FailingClient()

        with patch(
            "app.services.mandi_price_service.httpx.AsyncClient",
            return_value=client,
        ), self.assertLogs(
            "app.services.mandi_price_service", level="WARNING"
        ) as captured:
            first = await service.fetch_prices("Rice", state="Madhya Pradesh")
            second = await service.fetch_prices("Rice", state="Madhya Pradesh")

        self.assertEqual(first, [])
        self.assertEqual(second, [])
        self.assertEqual(client.calls, 1)
        messages = [line for line in captured.output if "temporarily unavailable" in line]
        self.assertEqual(len(messages), 1)
        self.assertIn("ReadTimeout", messages[0])

    async def test_missing_api_key_never_generates_mock_prices(self):
        service = MandiPriceService()
        service.api_key = None

        result = await service.fetch_prices("Rice", state="Madhya Pradesh")

        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
