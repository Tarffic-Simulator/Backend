from pydantic import BaseModel
from typing import Any


class SavedSimulationResponse(BaseModel):
    id: int
    user_id: int
    engine_simulation_id: str
    data: Any

    model_config = {"from_attributes": True}
