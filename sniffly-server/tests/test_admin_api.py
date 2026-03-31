"""Tests for admin API routes."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import AsyncClient

from app.config import settings


class TestAdminStatsAPI:
    """Tests for /api/admin/stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_stats_success(self, async_client: AsyncClient, admin_token: str, mock_mongodb):
        """Test getting admin stats with valid admin token."""
        # Setup mock data
        mock_mongodb.users.count_documents = AsyncMock(side_effect=[12, 10])
        mock_mongodb.shares.count_documents = AsyncMock(side_effect=[156, 23])

        # Create async iterator for empty shares cursor
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
        data = response.json()
        assert "total_users" in data
        assert "active_users" in data
        assert "total_shares" in data
        assert "public_shares" in data
        assert "recent_shares" in data

    @pytest.mark.asyncio
    async def test_get_stats_unauthorized(self, async_client: AsyncClient):
        """Test getting admin stats without token."""
        response = await async_client.get("/api/admin/stats")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_stats_forbidden(self, async_client: AsyncClient, user_token: str):
        """Test getting admin stats with non-admin token."""
        response = await async_client.get(
            "/api/admin/stats",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403


class TestAdminUsersAPI:
    """Tests for /api/admin/users endpoints."""

    @pytest.mark.asyncio
    async def test_list_users_success(self, async_client: AsyncClient, admin_token: str, mock_mongodb):
        """Test listing users with valid admin token."""
        mock_users = [
            {
                "username": "admin",
                "created_at": datetime.utcnow(),
                "is_active": True,
            },
            {
                "username": "user1",
                "created_at": datetime.utcnow(),
                "is_active": True,
            },
        ]

        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.skip = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)

        async def async_iter():
            for user in mock_users:
                yield user

        mock_cursor.__aiter__ = MagicMock(return_value=async_iter())
        mock_mongodb.users.find = MagicMock(return_value=mock_cursor)
        mock_mongodb.users.count_documents = AsyncMock(return_value=2)
        mock_mongodb.shares.count_documents = AsyncMock(return_value=0)

        with patch('app.routers.admin.get_mongodb', return_value=mock_mongodb):
            response = await async_client.get(
                "/api/admin/users",
                headers={"Authorization": f"Bearer {admin_token}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert data["total"] == 2

    @pytest.mark.asyncio
    async def test_create_user_success(self, async_client: AsyncClient, admin_token: str, mock_mongodb):
        """Test creating a new user."""
        mock_mongodb.users.find_one = AsyncMock(return_value=None)
        mock_mongodb.users.insert_one = AsyncMock()

        with patch('app.routers.admin.get_mongodb', return_value=mock_mongodb):
            response = await async_client.post(
                "/api/admin/users",
                json={
                    "username": "newuser",
                    "password": "password123",
                    "is_active": True,
                },
                headers={"Authorization": f"Bearer {admin_token}"}
            )

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_user_duplicate(self, async_client: AsyncClient, admin_token: str, mock_mongodb):
        """Test creating user with existing username."""
        mock_mongodb.users.find_one = AsyncMock(return_value={"username": "existinguser"})

        with patch('app.routers.admin.get_mongodb', return_value=mock_mongodb):
            response = await async_client.post(
                "/api/admin/users",
                json={
                    "username": "existinguser",
                    "password": "password123",
                    "is_active": True,
                },
                headers={"Authorization": f"Bearer {admin_token}"}
            )

        assert response.status_code == 409
        assert response.json()["detail"] == "Username already exists"

    @pytest.mark.asyncio
    async def test_create_user_invalid_password(self, async_client: AsyncClient, admin_token: str):
        """Test creating user with password too short."""
        response = await async_client.post(
            "/api/admin/users",
            json={
                "username": "newuser",
                "password": "short",  # Less than 8 characters
                "is_active": True,
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_update_user_password(self, async_client: AsyncClient, admin_token: str, mock_mongodb):
        """Test updating user password."""
        mock_mongodb.users.find_one = AsyncMock(return_value={
            "username": "testuser",
            "created_at": datetime.utcnow(),
            "is_active": True,
        })
        mock_mongodb.users.update_one = AsyncMock()
        mock_mongodb.shares.count_documents = AsyncMock(return_value=5)

        with patch('app.routers.admin.get_mongodb', return_value=mock_mongodb):
            response = await async_client.put(
                "/api/admin/users/testuser",
                json={"password": "newpassword123"},
                headers={"Authorization": f"Bearer {admin_token}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, async_client: AsyncClient, admin_token: str, mock_mongodb):
        """Test updating non-existent user."""
        mock_mongodb.users.find_one = AsyncMock(return_value=None)

        with patch('app.routers.admin.get_mongodb', return_value=mock_mongodb):
            response = await async_client.put(
                "/api/admin/users/nonexistent",
                json={"is_active": False},
                headers={"Authorization": f"Bearer {admin_token}"}
            )

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    @pytest.mark.asyncio
    async def test_delete_user_success(self, async_client: AsyncClient, admin_token: str, mock_mongodb):
        """Test deleting a user."""
        mock_mongodb.users.find_one = AsyncMock(return_value={
            "username": "deleteme",
            "created_at": datetime.utcnow(),
        })
        mock_mongodb.users.delete_one = AsyncMock()

        with patch('app.routers.admin.get_mongodb', return_value=mock_mongodb):
            response = await async_client.delete(
                "/api/admin/users/deleteme",
                headers={"Authorization": f"Bearer {admin_token}"}
            )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_self_forbidden(self, async_client: AsyncClient, admin_token: str, mock_mongodb):
        """Test that admin cannot delete themselves."""
        with patch('app.routers.admin.get_mongodb', return_value=mock_mongodb):
            response = await async_client.delete(
                f"/api/admin/users/{settings.admin_username}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )

        assert response.status_code == 400
        assert response.json()["detail"] == "Cannot delete yourself"


class TestAdminSharesAPI:
    """Tests for /api/admin/shares endpoints."""

    @pytest.mark.asyncio
    async def test_list_shares_success(self, async_client: AsyncClient, admin_token: str, mock_mongodb, sample_share):
        """Test listing shares with valid admin token."""
        mock_shares = [sample_share]

        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.skip = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)

        async def async_iter():
            for share in mock_shares:
                yield share

        mock_cursor.__aiter__ = MagicMock(return_value=async_iter())
        mock_mongodb.shares.find = MagicMock(return_value=mock_cursor)
        mock_mongodb.shares.count_documents = AsyncMock(return_value=1)

        with patch('app.routers.admin.get_mongodb', return_value=mock_mongodb):
            response = await async_client.get(
                "/api/admin/shares",
                headers={"Authorization": f"Bearer {admin_token}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "shares" in data
        assert "total" in data
        assert len(data["shares"]) == 1
        assert data["shares"][0]["id"] == sample_share["_id"]

    @pytest.mark.asyncio
    async def test_delete_share_success(self, async_client: AsyncClient, admin_token: str, mock_mongodb):
        """Test deleting a share."""
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        mock_mongodb.shares.delete_one = AsyncMock(return_value=mock_result)

        with patch('app.routers.admin.get_mongodb', return_value=mock_mongodb):
            response = await async_client.delete(
                "/api/admin/shares/test-share-id",
                headers={"Authorization": f"Bearer {admin_token}"}
            )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_share_not_found(self, async_client: AsyncClient, admin_token: str, mock_mongodb):
        """Test deleting non-existent share."""
        mock_result = MagicMock()
        mock_result.deleted_count = 0
        mock_mongodb.shares.delete_one = AsyncMock(return_value=mock_result)

        with patch('app.routers.admin.get_mongodb', return_value=mock_mongodb):
            response = await async_client.delete(
                "/api/admin/shares/nonexistent",
                headers={"Authorization": f"Bearer {admin_token}"}
            )

        assert response.status_code == 404
        assert response.json()["detail"] == "Share not found"
