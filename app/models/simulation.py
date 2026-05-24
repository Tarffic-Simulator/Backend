from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.types import TypeDecorator

from app.core.database import Base
from app.core.crypto import encrypt_json_payload, decrypt_json_payload


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

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    engine_simulation_id = Column(String(100), nullable=False)
    data = Column(EncryptedJSON, nullable=False)  # Stored encrypted, exposed as decrypted JSON