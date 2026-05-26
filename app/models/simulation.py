from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator

from app.core.crypto import decrypt_json_payload, encrypt_json_payload
from app.core.database import Base


class EncryptedJSON(TypeDecorator):
    """Store JSON-serializable values encrypted as text in the database."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return encrypt_json_payload(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return decrypt_json_payload(value)


class SavedSimulation(Base):
    __tablename__ = "saved_simulations"
    __table_args__ = (
        UniqueConstraint("user_id", "engine_simulation_id", name="uq_user_simulation"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    engine_simulation_id = Column(String(100), nullable=False)
    data = Column(EncryptedJSON, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="simulations")
