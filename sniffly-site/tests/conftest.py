"""Pytest configuration and fixtures for sniffly integration tests."""

import subprocess
import time

import pytest
import requests


COMPOSE_FILE = "docker-compose.test.yml"
BASE_URL = "http://localhost:8001"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
MAX_RETRIES = 30
RETRY_INTERVAL = 2


@pytest.fixture(scope="module")
def docker_services():
    """Start Docker services for testing and clean up after tests."""
    # Clean up any existing containers/volumes
    subprocess.run(
        ["docker-compose", "-f", COMPOSE_FILE, "down", "-v"],
        capture_output=True,
    )

    # Start services
    subprocess.run(
        ["docker-compose", "-f", COMPOSE_FILE, "up", "-d", "--build"],
        check=True,
        timeout=300,
    )

    # Wait for API to be healthy
    for i in range(MAX_RETRIES):
        try:
            response = requests.get(f"{BASE_URL}/", timeout=5)
            if response.status_code == 200:
                break
        except requests.exceptions.RequestException:
            pass
        if i < MAX_RETRIES - 1:
            time.sleep(RETRY_INTERVAL)
    else:
        # Cleanup before raising
        subprocess.run(["docker-compose", "-f", COMPOSE_FILE, "down", "-v"], capture_output=True)
        raise RuntimeError("API failed to become healthy within timeout period")

    yield

    # Teardown: stop and remove containers
    subprocess.run(
        ["docker-compose", "-f", COMPOSE_FILE, "down", "-v"],
        capture_output=True,
    )


@pytest.fixture(scope="module")
def admin_token(docker_services):
    """Get admin access token by logging in."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    response.raise_for_status()
    return response.json()["access_token"]


@pytest.fixture
def api_client():
    """Return the base URL for the API."""
    return BASE_URL
