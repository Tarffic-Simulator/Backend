from typing import AsyncIterator
from fastapi import Request, HTTPException
from httpx import AsyncClient


def get_httpx_client(request: Request) -> AsyncClient:
    """Return the AsyncClient created at app startup.

    Raises a 500 HTTPException if the client is missing. This is intentional: in
    production we want a clear failure if the shared client wasn't initialized
    (e.g. startup event didn't run). If desired, tests can monkeypatch
    `request.app.state.httpx_client`.
    """
    client: AsyncClient | None = getattr(request.app.state, "httpx_client", None)
    if client is None:
        # Fail fast and loudly in production instead of silently creating resources.
        raise HTTPException(status_code=500, detail="HTTP client not initialized. Ensure application startup completed and httpx client was created.")
    return client
