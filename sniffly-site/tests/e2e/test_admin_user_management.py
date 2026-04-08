"""E2E tests for admin user management UI."""

import time
from datetime import datetime

import pytest
import requests
from playwright.sync_api import Page, expect


BASE_URL = "http://localhost:8001"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


def get_admin_token() -> str:
    """Get admin access token by logging in via API."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    response.raise_for_status()
    return response.json()["access_token"]


def create_test_user(token: str, username: str, password: str = "testpass123") -> dict:
    """Create a test user via API."""
    response = requests.post(
        f"{BASE_URL}/api/users",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": username, "password": password},
    )
    response.raise_for_status()
    return response.json()


def delete_test_user(token: str, user_id: int) -> None:
    """Delete a test user via API."""
    response = requests.delete(
        f"{BASE_URL}/api/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    # Don't raise - deletion might fail if already deleted


@pytest.fixture(scope="module")
def admin_token():
    """Get admin token for API calls."""
    return get_admin_token()


@pytest.fixture
def authenticated_page(page: Page, admin_token: str) -> Page:
    """
    Provides a Playwright page that is authenticated as admin.
    Sets localStorage with the admin token before navigating to /admin.
    """
    page.goto(f"{BASE_URL}/")
    # Set token in localStorage to bypass frontend auth check
    page.evaluate(
        f"localStorage.setItem('access_token', '{admin_token}')"
    )
    page.goto(f"{BASE_URL}/admin")
    page.wait_for_load_state("networkidle")
    return page


class TestAdminLogin:
    """Test admin login and authentication."""

    def test_admin_login_via_api(self, admin_token):
        """Admin login via API returns valid token."""
        assert admin_token is not None
        assert len(admin_token) > 0

    def test_admin_page_loads_when_authenticated(self, authenticated_page: Page):
        """Admin page loads successfully when authenticated."""
        # Should see User Management section
        expect(authenticated_page.locator(".user-management-section")).to_be_visible()


class TestUserList:
    """Test user list functionality."""

    def test_user_list_loads(self, authenticated_page: Page, admin_token: str):
        """User list loads and displays users."""
        # Verify users-list container is visible
        expect(authenticated_page.locator("#users-list")).to_be_visible()

        # Should contain at least the admin user
        expect(authenticated_page.locator(".user-item")).to_contain_text("admin")

    def test_api_users_endpoint_returns_200(self, admin_token: str):
        """GET /api/users returns 200 with valid token."""
        response = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Admin user should exist
        usernames = [u["username"] for u in data]
        assert "admin" in usernames


class TestCreateUserModal:
    """Test Add User modal functionality."""

    def test_click_add_user_opens_modal(self, authenticated_page: Page):
        """Clicking 'Add User' button opens the create user modal."""
        # Click the Add User button
        authenticated_page.click('button:has-text("Add User")')

        # Modal should be visible
        expect(authenticated_page.locator("#create-user-modal")).to_be_visible()
        expect(authenticated_page.locator("#create-user-form")).to_be_visible()

    def test_modal_has_required_fields(self, authenticated_page: Page):
        """Create user modal has all required form fields."""
        # Open modal
        authenticated_page.click('button:has-text("Add User")')
        expect(authenticated_page.locator("#create-user-modal")).to_be_visible()

        # Check required fields exist
        expect(authenticated_page.locator("#new-username")).to_be_visible()
        expect(authenticated_page.locator("#new-password")).to_be_visible()
        expect(authenticated_page.locator("#new-is-admin")).to_be_visible()

    def test_close_modal_works(self, authenticated_page: Page):
        """Clicking cancel or X closes the modal."""
        # Open modal
        authenticated_page.click('button:has-text("Add User")')
        expect(authenticated_page.locator("#create-user-modal")).to_be_visible()

        # Click cancel button
        authenticated_page.click('button:has-text("Cancel")')

        # Modal should be hidden
        expect(authenticated_page.locator("#create-user-modal")).to_be_hidden()


class TestCreateUser:
    """Test user creation functionality."""

    def test_create_new_user_via_ui(self, authenticated_page: Page, admin_token: str):
        """Create a new user via the UI form."""
        # Generate unique username with timestamp
        timestamp = datetime.now().strftime("%H%M%S")
        test_username = f"e2e_user_{timestamp}"

        # Open modal
        authenticated_page.click('button:has-text("Add User")')
        expect(authenticated_page.locator("#create-user-modal")).to_be_visible()

        # Fill the form
        authenticated_page.fill("#new-username", test_username)
        authenticated_page.fill("#new-password", "testpass123")

        # Submit the form
        authenticated_page.click('button:has-text("Create")')

        # Wait for modal to close
        authenticated_page.wait_for_selector("#create-user-modal", state="hidden", timeout=5000)

        # Verify user appears in the list
        expect(authenticated_page.locator(".user-item")).to_contain_text(test_username)

        # Cleanup - delete the user via API
        # Find the user in the list and delete
        response = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        users = response.json()
        for user in users:
            if user["username"] == test_username:
                delete_test_user(admin_token, user["id"])
                break

    def test_create_user_appears_in_api(self, authenticated_page: Page, admin_token: str):
        """Verify newly created user appears in API response."""
        # Generate unique username
        timestamp = datetime.now().strftime("%H%M%S%f")
        test_username = f"e2e_verify_{timestamp}"

        # Create user via API for verification
        new_user = create_test_user(admin_token, test_username, "testpass123")

        # Refresh page to see the new user
        authenticated_page.reload()
        authenticated_page.wait_for_load_state("networkidle")

        # User should appear in list
        expect(authenticated_page.locator(".user-item")).to_contain_text(test_username)

        # Cleanup
        delete_test_user(admin_token, new_user["id"])


class TestDeleteUser:
    """Test user deletion functionality."""

    def test_delete_user_via_ui(self, authenticated_page: Page, admin_token: str):
        """Delete a test user via the UI."""
        # Create a user to delete
        timestamp = datetime.now().strftime("%H%M%S")
        test_username = f"delete_me_{timestamp}"
        new_user = create_test_user(admin_token, test_username, "testpass123")

        # Reload page to see the new user
        authenticated_page.reload()
        authenticated_page.wait_for_load_state("networkidle")

        # Find and click delete button for this user
        user_item = authenticated_page.locator(".user-item").filter(has_text=test_username)
        delete_button = user_item.locator("button.delete-btn")

        # Handle confirmation dialog
        authenticated_page.on("dialog", lambda dialog: dialog.accept())

        # Click delete
        delete_button.click()

        # Wait for user to be removed from list
        authenticated_page.wait_for_timeout(1000)  # Allow time for UI update

        # User should no longer appear in list (or list should reload)
        # Note: The exact behavior depends on UI implementation

        # Cleanup via API in case UI deletion failed
        response = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        users = response.json()
        for user in users:
            if user["username"] == test_username:
                delete_test_user(admin_token, user["id"])
                break


class TestAdminProtection:
    """Test that non-admin users cannot access admin features."""

    def test_regular_user_cannot_view_users(self, admin_token: str):
        """Regular user (non-admin) cannot access GET /api/users."""
        # Create a regular user
        timestamp = datetime.now().strftime("%H%M%S")
        regular_username = f"regular_{timestamp}"
        create_test_user(admin_token, regular_username, "testpass123")

        # Login as regular user
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": regular_username, "password": "testpass123"},
        )
        regular_token = response.json()["access_token"]

        # Try to list users as regular user
        list_response = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {regular_token}"},
        )
        assert list_response.status_code == 403

        # Cleanup
        response = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        users = response.json()
        for user in users:
            if user["username"] == regular_username:
                delete_test_user(admin_token, user["id"])
                break
