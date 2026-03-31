"""Tests for Pydantic models."""

from datetime import datetime
import pytest
from pydantic import ValidationError

from app.models import (
    UserLogin,
    TokenResponse,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    ShareAdminItem,
    ShareListResponse,
    AdminStats,
)


class TestAuthModels:
    """Tests for authentication models."""

    def test_user_login_valid(self):
        """Test valid UserLogin model."""
        model = UserLogin(username="testuser", password="testpass")
        assert model.username == "testuser"
        assert model.password == "testpass"

    def test_user_login_missing_fields(self):
        """Test UserLogin with missing required fields."""
        with pytest.raises(ValidationError):
            UserLogin(username="testuser")  # Missing password

        with pytest.raises(ValidationError):
            UserLogin(password="testpass")  # Missing username

    def test_token_response_defaults(self):
        """Test TokenResponse with default values."""
        model = TokenResponse(
            access_token="test-token",
            expires_in=3600
        )
        assert model.token_type == "bearer"
        assert model.access_token == "test-token"
        assert model.expires_in == 3600


class TestAdminModels:
    """Tests for admin-related models."""

    def test_user_create_valid(self):
        """Test valid UserCreate model."""
        model = UserCreate(
            username="newuser",
            password="password123",
            is_active=True
        )
        assert model.username == "newuser"
        assert model.password == "password123"
        assert model.is_active is True

    def test_user_create_password_min_length(self):
        """Test UserCreate password minimum length validation."""
        with pytest.raises(ValidationError):
            UserCreate(username="newuser", password="short")  # Less than 8 chars

    def test_user_create_password_exact_min(self):
        """Test UserCreate with exact minimum password length."""
        model = UserCreate(username="newuser", password="12345678")  # Exactly 8 chars
        assert len(model.password) == 8

    def test_user_create_default_active(self):
        """Test UserCreate default is_active value."""
        model = UserCreate(username="newuser", password="password123")
        assert model.is_active is True

    def test_user_update_partial(self):
        """Test UserUpdate with partial fields."""
        model = UserUpdate(password="newpassword")
        assert model.password == "newpassword"
        assert model.is_active is None

    def test_user_update_both_fields(self):
        """Test UserUpdate with both fields."""
        model = UserUpdate(password="newpassword", is_active=False)
        assert model.password == "newpassword"
        assert model.is_active is False

    def test_user_response(self):
        """Test UserResponse model."""
        model = UserResponse(
            username="testuser",
            created_at=datetime.utcnow(),
            is_active=True,
            share_count=10
        )
        assert model.username == "testuser"
        assert model.is_active is True
        assert model.share_count == 10

    def test_user_response_default_share_count(self):
        """Test UserResponse default share_count."""
        model = UserResponse(
            username="testuser",
            created_at=datetime.utcnow(),
            is_active=True
        )
        assert model.share_count == 0

    def test_user_list_response(self):
        """Test UserListResponse model."""
        users = [
            UserResponse(
                username="user1",
                created_at=datetime.utcnow(),
                is_active=True
            ),
            UserResponse(
                username="user2",
                created_at=datetime.utcnow(),
                is_active=True
            ),
        ]
        model = UserListResponse(
            users=users,
            total=2,
            page=1,
            limit=20
        )
        assert len(model.users) == 2
        assert model.total == 2
        assert model.page == 1
        assert model.limit == 20


class TestShareModels:
    """Tests for share-related models."""

    def test_share_admin_item(self):
        """Test ShareAdminItem model."""
        model = ShareAdminItem(
            id="share-123",
            project_name="Test Project",
            created_by="testuser",
            created_at=datetime.utcnow(),
            is_public=True
        )
        assert model.id == "share-123"
        assert model.project_name == "Test Project"
        assert model.is_public is True

    def test_share_list_response(self):
        """Test ShareListResponse model."""
        shares = [
            ShareAdminItem(
                id="share-1",
                project_name="Project 1",
                created_by="user1",
                created_at=datetime.utcnow(),
                is_public=True
            ),
        ]
        model = ShareListResponse(
            shares=shares,
            total=100,
            page=1,
            limit=20
        )
        assert len(model.shares) == 1
        assert model.total == 100
        assert model.page == 1


class TestAdminStatsModel:
    """Tests for AdminStats model."""

    def test_admin_stats_valid(self):
        """Test valid AdminStats model."""
        recent_shares = [
            ShareAdminItem(
                id="share-1",
                project_name="Recent Project",
                created_by="user1",
                created_at=datetime.utcnow(),
                is_public=True
            ),
        ]
        model = AdminStats(
            total_users=10,
            active_users=8,
            total_shares=100,
            public_shares=25,
            recent_shares=recent_shares
        )
        assert model.total_users == 10
        assert model.active_users == 8
        assert model.total_shares == 100
        assert model.public_shares == 25
        assert len(model.recent_shares) == 1

    def test_admin_stats_empty_recent_shares(self):
        """Test AdminStats with empty recent_shares."""
        model = AdminStats(
            total_users=10,
            active_users=8,
            total_shares=100,
            public_shares=25,
            recent_shares=[]
        )
        assert len(model.recent_shares) == 0
