import pytest

from types import SimpleNamespace
from fastapi import HTTPException

from app.services.engine_client import fetch_simulation_data


class FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, responses: list):
        # responses is a list of either Exception instances or FakeResponse
        self._responses = responses
        self.calls = 0

    async def get(self, url, timeout=None):
        if self.calls >= len(self._responses):
            raise RuntimeError("No more responses configured")
        resp = self._responses[self.calls]
        self.calls += 1
        if isinstance(resp, Exception):
            raise resp
        return resp


@pytest.mark.asyncio
async def test_fetch_simulation_success():
    client = FakeClient([FakeResponse(200, {"ok": True})])
    result = await fetch_simulation_data("sim1", client=client)
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_fetch_simulation_retries_and_success():
    client = FakeClient([Exception("net"), FakeResponse(200, {"ok": True})])
    result = await fetch_simulation_data("sim2", client=client, retries=2)
    assert result == {"ok": True}
    assert client.calls == 2


@pytest.mark.asyncio
async def test_fetch_simulation_failure_after_retries():
    client = FakeClient([Exception("e1"), Exception("e2"), Exception("e3")])
    with pytest.raises(HTTPException) as excinfo:
        await fetch_simulation_data("sim3", client=client, retries=2)
    assert excinfo.value.status_code == 502
