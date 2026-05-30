"""Endpoints for managing saved simulations in the Backend database.

These routes handle the Backend's own persistence layer (saved_simulations
table).  Engine interaction (create / cancel / steps) lives in engine_proxy.py.
The one exception is POST /save/{simulation_id}, which fetches live data from
the Engine and persists it locally.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.http_client import get_httpx_client
from app.core.log_config import get_logger
from app.core.security import get_current_user
from app.models.simulation import SavedSimulation
from app.models.user import User
from app.schemas import SavedSimulationResponse
from app.services.engine_client import fetch_simulation_data

router = APIRouter()
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# List / retrieve saved simulations
# ---------------------------------------------------------------------------


@router.get(
    "/",
    response_model=list[SavedSimulationResponse],
    summary="List saved simulations for the current user",
)
async def list_simulations(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SavedSimulation]:
    result = await db.execute(
        select(SavedSimulation)
        .where(SavedSimulation.user_id == current_user.id)
        .order_by(SavedSimulation.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get(
    "/{record_id}",
    response_model=SavedSimulationResponse,
    summary="Get a single saved simulation by its database record ID",
)
async def get_saved_simulation(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SavedSimulation:
    result = await db.execute(
        select(SavedSimulation).where(
            SavedSimulation.id == record_id,
            SavedSimulation.user_id == current_user.id,
        )
    )
    sim = result.scalar_one_or_none()
    if sim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulación no encontrada",
        )
    return sim


# ---------------------------------------------------------------------------
# Save / delete
# ---------------------------------------------------------------------------


@router.post(
    "/save/{simulation_id}",
    response_model=SavedSimulationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Fetch a simulation from the Engine and persist it locally",
)
async def save_engine_simulation(
    simulation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    httpx_client: AsyncClient = Depends(get_httpx_client),
) -> SavedSimulation:
    logger.info(
        "User %s requested save for simulation_id=%s",
        current_user.username,
        simulation_id,
    )

    # Check for duplicate before hitting the Engine
    existing = await db.execute(
        select(SavedSimulation).where(
            SavedSimulation.user_id == current_user.id,
            SavedSimulation.engine_simulation_id == simulation_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La simulación ya fue guardada anteriormente",
        )

    engine_data = await fetch_simulation_data(simulation_id, client=httpx_client)

    record = SavedSimulation(
        user_id=current_user.id,
        engine_simulation_id=simulation_id,
        data=engine_data,
    )
    try:
        db.add(record)
        await db.commit()
        await db.refresh(record)
    except IntegrityError:
        logger.warning(
            "Duplicate simulation save blocked for simulation_id=%s user=%s",
            simulation_id,
            current_user.username,
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La simulación ya estaba guardada",
        )
    except Exception:
        logger.exception(
            "DB error saving simulation_id=%s for user %s",
            simulation_id,
            current_user.username,
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al guardar la simulación",
        )

    logger.info(
        "Simulation saved: id=%s simulation_id=%s user=%s",
        record.id,
        simulation_id,
        current_user.username,
    )
    return record


@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a saved simulation by its database record ID",
)
async def delete_simulation(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    logger.info(
        "User %s requested delete for simulation record_id=%d",
        current_user.username,
        record_id,
    )

    result = await db.execute(
        select(SavedSimulation).where(
            SavedSimulation.id == record_id,
            SavedSimulation.user_id == current_user.id,
        )
    )
    sim = result.scalar_one_or_none()
    if sim is None:
        logger.warning(
            "Simulation record_id=%d not found or not owned by user %s",
            record_id,
            current_user.username,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulación no encontrada",
        )

    try:
        await db.delete(sim)
        await db.commit()
    except Exception:
        logger.exception(
            "DB error deleting simulation record_id=%d for user %s",
            record_id,
            current_user.username,
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar la simulación",
        )

    logger.info(
        "Simulation record_id=%d successfully deleted by user %s",
        record_id,
        current_user.username,
    )
    return None


# DELETE /simulations/{id} endpoint for authenticated users
@router.delete("/simulations/{simulation_id}", status_code=204)
def delete_simulation(
    simulation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sim = db.query(SavedSimulation).filter(
        SavedSimulation.id == simulation_id,
        SavedSimulation.user_id == current_user.id
    ).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    db.delete(sim)
    db.commit()