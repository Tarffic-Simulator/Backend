from sqlalchemy import Column, Integer, String, JSON, ForeignKey
from app.core.database import Base

class SavedSimulation(Base):
    __tablename__ = "saved_simulations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    engine_simulation_id = Column(String(100), nullable=False)
    data = Column(JSON, nullable=False) # Guardamos el payload del engine