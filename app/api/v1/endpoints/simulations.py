from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.simulation import SavedSimulation
from app.services.engine_client import fetch_simulation_data

router = APIRouter()

@router.post("/save/{simulation_id}")
async def save_engine_simulation(
    simulation_id: str, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    # 1. Consumimos el engine externo
    engine_data = await fetch_simulation_data(simulation_id)
    
    # 2. Guardamos en nuestra base de datos MySQL
    new_record = SavedSimulation(
        user_id=current_user.id,
        engine_simulation_id=simulation_id,
        data=engine_data
    )
    db.add(new_record)
    db.commit()
    
    return {"message": "Simulación guardada", "data": engine_data}