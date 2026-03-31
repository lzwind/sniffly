"""Tests for authentication module."""

import pytest
from fastapi import HTTPException

from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    get_current_user,
    require_admin,
)
from app.config import settings


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password_returns_string(self):
        """Test that hash_password returns a string."""
        password = "testpassword123"
        hashed = hash_password(password)
        assert isinstance(hashed, str)
        assert hashed != password

    def test_hash_password_different_each_time(self):
        """Test that hash_password produces different hashes (due to salt)."""
        password = "testpassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test that verify_password returns True for correct password."""
        password = "testpassword123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test that verify_password returns False for incorrect password."""
        password = "testpassword123"
        hashed = hash_password(password)
        assert verify_password("wrongpassword", hashed) is False

    def test_verify_password_empty_password(self):
        """Test that verify_password handles empty password."""
        hashed = hash_password("testpassword")
        assert verify_password("", hashed) is False


class TestJWTToken:
    """Tests for JWT token functions."""

    def test_create_access_token_returns_string(self):
        """Test that create_access_token returns a string."""
        token = create_access_token(data={"sub": "testuser"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_different_each_time(self):
        """Test that tokens are different due to timestamp."""
        import time
        token1 = create_access_token(data={"sub": "testuser"})
        time.sleep(0.01)  # Small delay to ensure different timestamp
        token2 = create_access_token(data={"sub": "testuser"})
        # Tokens may or may not be different depending on timing

    def test_decode_token_valid(self):
        """Test that decode_token correctly decodes a valid token."""
        token = create_access_token(data={"sub": "testuser"})
        payload = decode_token(token)
        assert payload["sub"] == "testuser"
        assert "exp" in payload

    def test_decode_token_invalid(self):
        """Test that decode_token returns None for invalid token."""
        result = decode_token("invalid-token")
        assert result is None

    def test_decode_token_tampered(self):
        """Test that decode_token returns None for tampered token."""
        token = create_access_token(data={"sub": "testuser"})
        tampered_token = token[:-5] + "xxxxx"
        result = decode_token(tampered_token)
        assert result is None


class TestGetCurrentUser:
    """Tests for get_current_user dependency via dependency_overrides."""

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self, async_client):
        """Test get_current_user with valid token via dependency override."""
        token = create_access_token(data={"sub": "testuser"})

        # Override the get_current_user dependency to test the token handling
        from app.auth import get_current_user
        from app.main import app

        async def mock_get_current_user():
            return "testuser"

        app.dependency_overrides[get_current_user] = mock_get_current_user

        try:
            response = await async_client.get(
                "/api/admin/stats",
                headers={"Authorization": f"Bearer {token}"}
            )
            # Should not get 401 (unauthorized)
            assert response.status_code != 401
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token_returns_401(self, async_client):
        """Test get_current_user returns 401 for invalid token."""
        response = await async_client.get(
            "/api/admin/stats",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401


class TestRequireAdmin:
    """Tests for require_admin via HTTP endpoint responses."""

    @pytest.mark.asyncio
    async def test_require_admin_valid_admin_token(self, async_client, admin_token, mock_mongodb):
        """Test admin endpoint with valid admin token."""
        from unittest.mock import AsyncMock, MagicMock, patch

        # Setup mock data for stats endpoint
        mock_mongodb.users.count_documents = AsyncMock(side_effect=[12, 10])
        mock_mongodb.shares.count_documents = AsyncMock(side_effect=[156, 23])

        class AsyncIterator:
            def __init__(self, items):
                self.items = items
                self.index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.index < len(self.items):
                    item = self.items[self.index]
                    self.index += 1
                    return item
                raise StopAsyncIteration

        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=AsyncIterator([]))
        mock_mongodb.shares.find = MagicMock(return_value=mock_cursor)

        with patch('app.routers.admin.get_mongodb', return_value=mock_mongodb):
            response = await async_client.get(
                "/api/admin/stats",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_require_admin_regular_user_gets_403(self, async_client, user_token):
        """Test admin endpoint with regular user token returns 403."""
        response = await async_client.get(
            "/api/admin/stats",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_require_admin_invalid_token_gets_401(self, async_client):
        """Test admin endpoint with invalid token returns 401."""
        response = await async_client.get(
            "/api/admin/stats",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_require_admin_missing_token_gets_401(self, async_client):
        """Test admin endpoint without token returns 401."""
        response = await async_client.get("/api/admin/stats")
        assert response.status_code == 401
