"""Pytest fixtures for sniffly-server tests."""

import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.auth import create_access_token, hash_password
from app.config import settings


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_mongodb():
    """Mock MongoDB database."""
    mock_db = MagicMock()
    mock_db.users = MagicMock()
    mock_db.shares = MagicMock()
    return mock_db


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock_client = AsyncMock()
    return mock_client


@pytest.fixture
def admin_token() -> str:
    """Generate admin JWT token for testing."""
    return create_access_token(data={"sub": settings.admin_username})


@pytest.fixture
def user_token() -> str:
    """Generate regular user JWT token for testing."""
    return create_access_token(data={"sub": "regular_user"})


@pytest.fixture
def test_client() -> TestClient:
    """Create test client for sync tests."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_user() -> dict:
    """Sample user data for testing."""
    return {
        "username": "testuser",
        "password": "testpassword123",
        "is_active": True,
    }


@pytest.fixture
def sample_share() -> dict:
    """Sample share data for testing."""
    return {
        "_id": "test-share-id-123",
        "project_name": "Test Project",
        "created_by": "testuser",
        "created_at": "2026-03-31T10:00:00Z",
        "is_public": True,
        "statistics": {
            "overview": {
                "total_tokens": {"input": 1000, "output": 2000},
            },
            "user_interactions": {
                "user_commands_analyzed": 50,
            },
        },
        "charts": [],
        "user_commands": [],
        "version": "0.1.5",
    }
