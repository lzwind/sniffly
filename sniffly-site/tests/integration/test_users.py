"""Integration tests for users API (admin only)."""

import requests

from tests.conftest import docker_services, admin_token, api_client


class TestUsersList:
    """Test GET /api/users."""

    def test_admin_list_users(self, docker_services, admin_token, api_client):
        """admin 列出用户返回 200 + 用户列表."""
        response = requests.get(
            f"{api_client}/api/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # Should contain admin user
        usernames = [u["username"] for u in data]
        assert "admin" in usernames

    def test_regular_user_list_users(self, docker_services, admin_token, api_client):
        """普通用户列用户返回 403."""
        # First create a regular (non-admin) user
        create_response = requests.post(
            f"{api_client}/api/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"username": "regular_user_123", "password": "pass123"},
        )
        assert create_response.status_code == 200

        # Login as the regular user
        login_response = requests.post(
            f"{api_client}/api/auth/login",
            json={"username": "regular_user_123", "password": "pass123"},
        )
        assert login_response.status_code == 200
        regular_token = login_response.json()["access_token"]

        # Try to list users as regular user
        response = requests.get(
            f"{api_client}/api/users",
            headers={"Authorization": f"Bearer {regular_token}"},
        )
        assert response.status_code == 403

    def test_not_logged_in(self, docker_services, api_client):
        """未登录访问返回 401."""
        response = requests.get(f"{api_client}/api/users")
        assert response.status_code == 401


class TestUsersCreate:
    """Test POST /api/users."""

    def test_admin_create_user(self, docker_services, admin_token, api_client):
        """admin 创建用户返回 200 + 用户信息."""
        response = requests.post(
            f"{api_client}/api/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"username": "newuser_abc", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newuser_abc"
        assert data["is_admin"] is False
        assert "id" in data

    def test_duplicate_username(self, docker_services, admin_token, api_client):
        """重复用户名返回 400."""
        # Create a user first
        requests.post(
            f"{api_client}/api/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"username": "duplicate_user_xyz", "password": "pass123"},
        )

        # Try to create another user with same username
        response = requests.post(
            f"{api_client}/api/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"username": "duplicate_user_xyz", "password": "anotherpass"},
        )
        assert response.status_code == 400

    def test_admin_create_admin(self, docker_services, admin_token, api_client):
        """admin 创建 admin 用户返回 200."""
        response = requests.post(
            f"{api_client}/api/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"username": "newadmin_xyz", "password": "adminpass123", "is_admin": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newadmin_xyz"
        assert data["is_admin"] is True


class TestUsersDelete:
    """Test DELETE /api/users/{user_id}."""

    def test_admin_delete_user(self, docker_services, admin_token, api_client):
        """admin 删除用户返回 200."""
        # Create a user to delete
        create_response = requests.post(
            f"{api_client}/api/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"username": "user_to_delete_123", "password": "pass123"},
        )
        assert create_response.status_code == 200
        user_id = create_response.json()["id"]

        # Delete the user
        delete_response = requests.delete(
            f"{api_client}/api/users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert delete_response.status_code == 200

    def test_admin_self_delete(self, docker_services, admin_token, api_client):
        """admin 自删除返回 400."""
        # admin user has id=1 from init.sql seeding
        delete_response = requests.delete(
            f"{api_client}/api/users/1",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert delete_response.status_code == 400


class TestUserShares:
    """Test GET /api/users/{user_id}/shares."""

    def test_admin_get_user_shares(self, docker_services, admin_token, api_client):
        """admin 查看用户分享返回 200 + 分享列表."""
        # Create a user and their share
        create_user_response = requests.post(
            f"{api_client}/api/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"username": "share_owner_123", "password": "pass123"},
        )
        assert create_user_response.status_code == 200
        user_id = create_user_response.json()["id"]

        # Login as the share owner
        login_response = requests.post(
            f"{api_client}/api/auth/login",
            json={"username": "share_owner_123", "password": "pass123"},
        )
        assert login_response.status_code == 200
        owner_token = login_response.json()["access_token"]

        # Create a share for this user
        share_response = requests.post(
            f"{api_client}/api/shares",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "project_name": "test-share-project",
                "stats": {"views": 10},
                "user_commands": [
                    {"timestamp": "2024-01-01T00:00:00", "hash": "abc123"}
                ],
            },
        )
        assert share_response.status_code == 200

        # Admin gets user's shares
        get_shares_response = requests.get(
            f"{api_client}/api/users/{user_id}/shares",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert get_shares_response.status_code == 200
        shares = get_shares_response.json()
        assert isinstance(shares, list)
        assert len(shares) >= 1
        assert shares[0]["project_name"] == "test-share-project"
