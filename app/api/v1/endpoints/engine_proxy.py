"""Proxy endpoints that forward authenticated requests to the Engine service.

All routes here require a valid JWT.  The Backend validates the token, then
forwards the call to the Engine and returns the Engine response verbatim.
This keeps the frontend talking only to the Backend while the Engine stays
internal.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from httpx import AsyncClient

from app.core.http_client import get_httpx_client
from app.core.log_config import get_logger
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.engine import (
    CreateSimulationRequest,
    GeographicAreaSummaryResponse,
    GeographicAreaTopologyResponse,
    SimulationRecordResponse,
    SimulationStepResponse,
    CancelSimulationResponse,
)
from app.services.engine_client import (
    cancel_engine_simulation,
    create_engine_simulation,
    fetch_geographic_area_topology,
    fetch_geographic_areas,
    fetch_simulation_data,
    fetch_simulation_steps,
)

router = APIRouter()
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Geographic areas
# ---------------------------------------------------------------------------


@router.get(
    "/geographic-areas",
    response_model=list[GeographicAreaSummaryResponse],
    summary="List geographic areas available in the Engine",
)
async def list_geographic_areas(
    current_user: User = Depends(get_current_user),
    client: AsyncClient = Depends(get_httpx_client),
) -> list[dict[str, Any]]:
    logger.debug("User %s listing geographic areas", current_user.username)
    return await fetch_geographic_areas(client)


@router.get(
    "/geographic-areas/{area_id}/topology",
    response_model=GeographicAreaTopologyResponse,
    summary="Get topology for a geographic area",
)
async def get_geographic_area_topology(
    area_id: str,
    current_user: User = Depends(get_current_user),
    client: AsyncClient = Depends(get_httpx_client),
) -> dict[str, Any]:
    logger.debug(
        "User %s fetching topology for area_id=%s", current_user.username, area_id
    )
    return await fetch_geographic_area_topology(area_id, client)


# ---------------------------------------------------------------------------
# Simulations
# ---------------------------------------------------------------------------


@router.post(
    "/simulations",
    response_model=SimulationRecordResponse,
    status_code=201,
    summary="Create a new simulation in the Engine",
)
async def create_simulation(
    request: CreateSimulationRequest,
    current_user: User = Depends(get_current_user),
    client: AsyncClient = Depends(get_httpx_client),
) -> dict[str, Any]:
    logger.info(
        "User %s creating simulation for area_id=%s",
        current_user.username,
        request.area_id,
    )
    return await create_engine_simulation(request.model_dump(), client)


@router.get(
    "/simulations/{simulation_id}",
    response_model=SimulationRecordResponse,
    summary="Get a simulation record from the Engine",
)
async def get_simulation(
    simulation_id: str,
    current_user: User = Depends(get_current_user),
    client: AsyncClient = Depends(get_httpx_client),
) -> dict[str, Any]:
    logger.debug(
        "User %s fetching simulation_id=%s", current_user.username, simulation_id
    )
    return await fetch_simulation_data(simulation_id, client)


@router.post(
    "/simulations/{simulation_id}/cancel",
    response_model=CancelSimulationResponse,
    summary="Cancel a running simulation in the Engine",
)
async def cancel_simulation(
    simulation_id: str,
    current_user: User = Depends(get_current_user),
    client: AsyncClient = Depends(get_httpx_client),
) -> dict[str, Any]:
    logger.info(
        "User %s cancelling simulation_id=%s", current_user.username, simulation_id
    )
    return await cancel_engine_simulation(simulation_id, client)


@router.get(
    "/simulations/{simulation_id}/steps",
    response_model=list[SimulationStepResponse],
    summary="List all recorded steps for a simulation",
)
async def list_simulation_steps(
    simulation_id: str,
    current_user: User = Depends(get_current_user),
    client: AsyncClient = Depends(get_httpx_client),
) -> list[dict[str, Any]]:
    logger.debug(
        "User %s listing steps for simulation_id=%s",
        current_user.username,
        simulation_id,
    )
    return await fetch_simulation_steps(simulation_id, client)
