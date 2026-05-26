from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SavedSimulationResponse(BaseModel):
    id: int
    user_id: int
    engine_simulation_id: str
    data: Any
    created_at: datetime

    model_config = {"from_attributes": True}
