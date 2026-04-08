"""Integration tests for authentication API."""

import requests

from tests.conftest import docker_services, admin_token, api_client


class TestAuthLogin:
    """Test POST /api/auth/login."""

    def test_correct_credentials(self, docker_services, api_client):
        """正确账号密码登录返回 200 + token."""
        response = requests.post(
            f"{api_client}/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_wrong_password(self, docker_services, api_client):
        """错误密码返回 401."""
        # Use admin user with wrong password
        response = requests.post(
            f"{api_client}/api/auth/login",
            json={"username": "admin", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_nonexistent_user(self, docker_services, api_client):
        """不存在用户返回 401."""
        response = requests.post(
            f"{api_client}/api/auth/login",
            json={"username": "nonexistent_user_12345", "password": "anypassword"},
        )
        assert response.status_code == 401


class TestAuthToken:
    """Test POST /api/auth/token (OAuth2 Password Grant)."""

    def test_oauth2_password_grant(self, docker_services, api_client):
        """OAuth2 Password Grant 返回 200 + token."""
        response = requests.post(
            f"{api_client}/api/auth/token",
            data={
                "grant_type": "password",
                "username": "admin",
                "password": "admin123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data


class TestAuthMe:
    """Test GET /api/auth/me."""

    def test_logged_in_get_user_info(self, docker_services, admin_token, api_client):
        """已登录获取用户信息返回 200 + 用户信息."""
        response = requests.get(
            f"{api_client}/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "username" in data
        assert data["username"] == "admin"

    def test_not_logged_in(self, docker_services, api_client):
        """未登录访问 /me 返回 401."""
        response = requests.get(f"{api_client}/api/auth/me")
        assert response.status_code == 401

    def test_invalid_token(self, docker_services, api_client):
        """无效 token 访问 /me 返回 401."""
        response = requests.get(
            f"{api_client}/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_123"},
        )
        assert response.status_code == 401


class TestAuthLogout:
    """Test POST /api/auth/logout."""

    def test_logout(self, docker_services, admin_token, api_client):
        """登出返回 200."""
        response = requests.post(
            f"{api_client}/api/auth/logout",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
