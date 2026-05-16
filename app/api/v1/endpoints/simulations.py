from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.concurrency import run_in_threadpool
from typing import Any

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.http_client import get_httpx_client
from app.core.log_config import get_logger
from httpx import AsyncClient
from app.models.user import User
from app.models.simulation import SavedSimulation
from app.services.engine_client import fetch_simulation_data
from app.schemas import SavedSimulationResponse

router = APIRouter()
logger = get_logger(__name__)


async def _save_simulation_to_db(db: Session, record: SavedSimulation) -> SavedSimulation:
    try:
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    except Exception:
        db.rollback()
        raise


@router.post("/save/{simulation_id}", response_model=SavedSimulationResponse, status_code=status.HTTP_201_CREATED)
async def save_engine_simulation(
    simulation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    httpx_client: AsyncClient = Depends(get_httpx_client),
):
    logger.info("User %s requested save for simulation_id=%s", current_user.username, simulation_id)

    engine_data: Any = await fetch_simulation_data(simulation_id, client=httpx_client)

    new_record = SavedSimulation(
        user_id=current_user.id,
        engine_simulation_id=simulation_id,
        data=engine_data,
    )

    try:
        saved = await run_in_threadpool(_save_simulation_to_db, db, new_record)
    except Exception:
        logger.exception("DB error saving simulation_id=%s for user %s", simulation_id, current_user.username)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al guardar la simulaci\u00f3n")

    logger.info("Simulation saved: id=%s simulation_id=%s user=%s", saved.id, simulation_id, current_user.username)
    return saved