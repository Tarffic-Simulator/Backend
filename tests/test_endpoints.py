"""Integration and unit tests for the newly added endpoints."""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import status
from fastapi.testclient import TestClient

# Set mock environment variables before importing app
os.environ["SECRET_KEY"] = "12345678901234567890123456789012"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["ENGINE_API_URL"] = "http://localhost:8000"

from app.main import app
from app.core.security import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.simulation import SavedSimulation

client = TestClient(app)

# A fake current user for dependency injection
fake_user = User(id=1, username="testuser")


def get_current_user_override():
    return fake_user


@pytest.fixture(autouse=True)
def run_around_tests():
    # Setup: override current user dependency
    app.dependency_overrides[get_current_user] = get_current_user_override
    yield
    # Teardown: clear overrides
    app.dependency_overrides.clear()


def test_get_me_success():
    """Test GET /api/v1/auth/me returns the current logged-in user."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["username"] == "testuser"
    assert data["id"] == 1


def test_get_me_unauthorized():
    """Test GET /api/v1/auth/me returns 401 if unauthorized."""
    # Remove override to trigger oauth2 scheme check
    app.dependency_overrides.clear()
    response = client.get("/api/v1/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_delete_simulation_success():
    """Test DELETE /api/v1/simulations/{record_id} successfully deletes own simulation."""
    # Mock database session
    mock_db = AsyncMock()

    # Mock the execute result for finding the simulation
    mock_sim = SavedSimulation(
        id=42, user_id=fake_user.id, engine_simulation_id="sim-abc"
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_sim
    mock_db.execute.return_value = mock_result

    # Override get_db to yield our mock_db
    async def get_db_override():
        yield mock_db

    app.dependency_overrides[get_db] = get_db_override

    response = client.delete("/api/v1/simulations/42")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify db.delete and db.commit were called
    mock_db.delete.assert_called_once_with(mock_sim)
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_simulation_not_found():
    """Test DELETE /api/v1/simulations/{record_id} returns 404 if simulation not found or not owned."""
    # Mock database session
    mock_db = AsyncMock()

    # Return None for scalar_one_or_none
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    async def get_db_override():
        yield mock_db

    app.dependency_overrides[get_db] = get_db_override

    response = client.delete("/api/v1/simulations/99")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Simulación no encontrada"

    # Verify no deletion took place
    mock_db.delete.assert_not_called()
    mock_db.commit.assert_not_called()
