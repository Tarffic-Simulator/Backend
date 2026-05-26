"""Tests for the engine client retry and error handling behavior."""

import pytest

from fastapi import HTTPException

from app.services.engine_client import fetch_simulation_data


class FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        """Create a minimal HTTP-like response for test scenarios."""
        self.status_code = status_code
        self._payload = payload

    def json(self):
        """Return the configured JSON payload."""
        return self._payload


class FakeClient:
    def __init__(self, responses: list):
        """Create a fake async client that replays predefined outcomes."""
        self._responses = responses
        self.calls = 0

    async def get(self, url, timeout=None):
        """Return the next configured response or raise the next exception."""
        if self.calls >= len(self._responses):
            raise RuntimeError("No more responses configured")
        resp = self._responses[self.calls]
        self.calls += 1
        if isinstance(resp, Exception):
            raise resp
        return resp


@pytest.mark.asyncio
async def test_fetch_simulation_success():
    """It returns the engine payload when the first request succeeds."""
    client = FakeClient([FakeResponse(200, {"ok": True})])
    result = await fetch_simulation_data("sim1", client=client)
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_fetch_simulation_retries_and_success():
    """It retries transient failures and eventually returns data."""
    client = FakeClient([Exception("net"), FakeResponse(200, {"ok": True})])
    result = await fetch_simulation_data("sim2", client=client, retries=2)
    assert result == {"ok": True}
    assert client.calls == 2


@pytest.mark.asyncio
async def test_fetch_simulation_failure_after_retries():
    """It raises a gateway error after exhausting all retries."""
    client = FakeClient([Exception("e1"), Exception("e2"), Exception("e3")])
    with pytest.raises(HTTPException) as excinfo:
        await fetch_simulation_data("sim3", client=client, retries=2)
    assert excinfo.value.status_code == 502
