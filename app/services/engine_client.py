"""Client helpers for communicating with the Engine service."""

import asyncio
from fastapi import HTTPException
from httpx import AsyncClient

from app.core.config import settings
from app.core.log_config import get_logger

logger = get_logger(__name__)


async def fetch_simulation_data(
    simulation_id: str,
    client: AsyncClient,
    retries: int = 2,
) -> dict:
    """Fetch simulation data from the Engine service with retry handling."""
    url = f"{settings.engine_api_url}/simulations/{simulation_id}"
    timeout_seconds = 5.0
    for attempt in range(retries + 1):
        try:
            logger.debug(
                "Fetching simulation_id=%s from engine (attempt %d/%d)",
                simulation_id,
                attempt + 1,
                retries + 1,
            )
            response = await client.get(url, timeout=timeout_seconds)
            if response.status_code != 200:
                logger.warning(
                    "Engine returned %d for simulation_id=%s",
                    response.status_code,
                    simulation_id,
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Error al contactar al Engine",
                )
            logger.info("Engine response OK for simulation_id=%s", simulation_id)
            return response.json()
        except HTTPException:
            raise
        except Exception as exc:
            if attempt == retries:
                logger.error(
                    "Engine unreachable for simulation_id=%s after %d attempts: %s",
                    simulation_id,
                    retries + 1,
                    exc,
                )
                raise HTTPException(
                    status_code=502, detail=f"Engine unreachable: {str(exc)}"
                )
            logger.warning(
                "Engine attempt %d failed for simulation_id=%s: %s — retrying",
                attempt + 1,
                simulation_id,
                exc,
            )
            await asyncio.sleep(0.5 * (attempt + 1))
