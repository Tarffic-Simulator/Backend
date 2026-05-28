"""Client helpers for communicating with the Engine service."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import HTTPException
from httpx import AsyncClient

from app.core.config import settings
from app.core.log_config import get_logger

logger = get_logger(__name__)

_RETRIES_DEFAULT = 2
_TIMEOUT_DEFAULT = 10.0


def _engine_error_detail(response: Any) -> str:
    """Extract the most useful error message from an Engine response."""
    try:
        payload = response.json()
    except Exception:
        return response.text.strip() or f"Engine error ({response.status_code})"

    if isinstance(payload, dict):
        for key in ("detail", "message", "error"):
            message = payload.get(key)
            if isinstance(message, str) and message.strip():
                return message.strip()
        return str(payload)

    if payload is None:
        return f"Engine error ({response.status_code})"

    return str(payload)


async def _get(
    client: AsyncClient,
    path: str,
    *,
    retries: int = _RETRIES_DEFAULT,
    timeout: float = _TIMEOUT_DEFAULT,
) -> dict[str, Any]:
    """GET helper with retry/back-off against the Engine base URL."""
    url = f"{settings.engine_api_url}{path}"
    for attempt in range(retries + 1):
        try:
            logger.debug("Engine GET %s (attempt %d/%d)", url, attempt + 1, retries + 1)
            response = await client.get(url, timeout=timeout)
            if response.status_code != 200:
                logger.warning(
                    "Engine returned %d for GET %s", response.status_code, url
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Engine error: {_engine_error_detail(response)}",
                )
            return response.json()
        except HTTPException:
            raise
        except Exception as exc:
            if attempt == retries:
                logger.error(
                    "Engine unreachable at %s after %d attempts: %s",
                    url,
                    retries + 1,
                    exc,
                )
                raise HTTPException(
                    status_code=502, detail=f"Engine unreachable: {exc}"
                )
            logger.warning(
                "Engine attempt %d failed for %s: %s — retrying", attempt + 1, url, exc
            )
            await asyncio.sleep(0.5 * (attempt + 1))


async def _post(
    client: AsyncClient,
    path: str,
    payload: dict[str, Any],
    *,
    expected_status: int = 201,
    retries: int = _RETRIES_DEFAULT,
    timeout: float = _TIMEOUT_DEFAULT,
) -> dict[str, Any]:
    """POST helper with retry/back-off against the Engine base URL."""
    url = f"{settings.engine_api_url}{path}"
    for attempt in range(retries + 1):
        try:
            logger.debug(
                "Engine POST %s (attempt %d/%d)", url, attempt + 1, retries + 1
            )
            response = await client.post(url, json=payload, timeout=timeout)
            if response.status_code != expected_status:
                logger.warning(
                    "Engine returned %d for POST %s", response.status_code, url
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Engine error: {_engine_error_detail(response)}",
                )
            return response.json()
        except HTTPException:
            raise
        except Exception as exc:
            if attempt == retries:
                logger.error(
                    "Engine unreachable at %s after %d attempts: %s",
                    url,
                    retries + 1,
                    exc,
                )
                raise HTTPException(
                    status_code=502, detail=f"Engine unreachable: {exc}"
                )
            logger.warning(
                "Engine attempt %d failed for %s: %s — retrying", attempt + 1, url, exc
            )
            await asyncio.sleep(0.5 * (attempt + 1))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def fetch_geographic_areas(client: AsyncClient) -> list[dict[str, Any]]:
    """Return the list of available geographic areas from the Engine."""
    return await _get(client, "/geographic-areas")


async def fetch_geographic_area_topology(
    area_id: str, client: AsyncClient
) -> dict[str, Any]:
    """Return the full topology for a geographic area."""
    return await _get(client, f"/geographic-areas/{area_id}/topology")


async def create_engine_simulation(
    payload: dict[str, Any], client: AsyncClient
) -> dict[str, Any]:
    """Create a new simulation in the Engine and return its record."""
    return await _post(client, "/simulations", payload, expected_status=201)


async def fetch_simulation_data(
    simulation_id: str,
    client: AsyncClient,
    retries: int = _RETRIES_DEFAULT,
) -> dict[str, Any]:
    """Fetch a simulation record from the Engine (kept for backwards compat)."""
    return await _get(client, f"/simulations/{simulation_id}", retries=retries)


async def check_engine_availability(client: AsyncClient) -> dict[str, Any]:
    """Probe the Engine health endpoint and return a normalized status payload."""
    url = f"{settings.engine_api_url}/health"
    try:
        response = await client.get(url, timeout=_TIMEOUT_DEFAULT)
        if response.status_code == 200:
            return {"status": "ok"}

        return {
            "status": "error",
            "detail": _engine_error_detail(response),
            "status_code": response.status_code,
        }
    except Exception as exc:
        logger.warning("Engine health probe failed for %s: %s", url, exc)
        return {"status": "error", "detail": str(exc), "status_code": 502}


async def cancel_engine_simulation(
    simulation_id: str, client: AsyncClient
) -> dict[str, Any]:
    """Send a cancel request to the Engine for the given simulation."""
    url = f"{settings.engine_api_url}/simulations/{simulation_id}/cancel"
    try:
        logger.debug("Engine POST cancel for simulation_id=%s", simulation_id)
        response = await client.post(url, timeout=_TIMEOUT_DEFAULT)
        if response.status_code not in (200, 409):
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Engine error: {response.text}",
            )
        return response.json()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Engine unreachable while cancelling %s: %s", simulation_id, exc)
        raise HTTPException(status_code=502, detail=f"Engine unreachable: {exc}")


async def fetch_simulation_steps(
    simulation_id: str, client: AsyncClient
) -> list[dict[str, Any]]:
    """Return all recorded steps for a simulation from the Engine."""
    return await _get(client, f"/simulations/{simulation_id}/steps")
