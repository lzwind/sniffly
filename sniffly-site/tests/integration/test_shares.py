"""Integration tests for shares API."""

import requests

from tests.conftest import docker_services, admin_token, api_client


class TestSharesList:
    """Test GET /api/shares."""

    def test_empty_list(self, docker_services, admin_token, api_client):
        """空列表返回 200 + []."""
        response = requests.get(
            f"{api_client}/api/shares",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_not_logged_in(self, docker_services, api_client):
        """未登录访问返回 401."""
        response = requests.get(f"{api_client}/api/shares")
        assert response.status_code == 401


class TestSharesCreate:
    """Test POST /api/shares."""

    def test_create_share(self, docker_services, admin_token, api_client):
        """创建分享返回 200 + uuid."""
        response = requests.post(
            f"{api_client}/api/shares",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "project_name": "test-project",
                "stats": {"views": 10},
                "user_commands": [
                    {"timestamp": "2024-01-01T00:00:00", "hash": "abc123"}
                ],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "uuid" in data
        assert data["project_name"] == "test-project"

    def test_create_and_get_share(self, docker_services, admin_token, api_client):
        """创建分享后能获取详情."""
        # Create share
        create_response = requests.post(
            f"{api_client}/api/shares",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "project_name": "test-get-project",
                "stats": {"views": 5},
                "user_commands": [
                    {"timestamp": "2024-01-01T00:00:00", "hash": "def456"}
                ],
            },
        )
        assert create_response.status_code == 200
        uuid = create_response.json()["uuid"]

        # Get share
        get_response = requests.get(
            f"{api_client}/api/shares/{uuid}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["uuid"] == uuid
        assert data["project_name"] == "test-get-project"
        assert data["stats"] == {"views": 5}
        assert len(data["user_commands"]) == 1

    def test_nonexistent_share(self, docker_services, admin_token, api_client):
        """不存在的分享返回 404."""
        response = requests.get(
            f"{api_client}/api/shares/nonexistent-uuid-12345",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404


class TestSharesMerge:
    """Test shares merge logic."""

    def test_merge_commands(self, docker_services, admin_token, api_client):
        """同一项目名再分享，uuid 不变，commands 去重合并."""
        project_name = "merge-test-project"

        # Create first share with command1
        response1 = requests.post(
            f"{api_client}/api/shares",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "project_name": project_name,
                "stats": {"views": 1},
                "user_commands": [
                    {"timestamp": "2024-01-01T00:00:00", "hash": "cmd1"}
                ],
            },
        )
        assert response1.status_code == 200
        data1 = response1.json()
        uuid = data1["uuid"]

        # Get share to verify user_commands
        get1_response = requests.get(
            f"{api_client}/api/shares/{uuid}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert get1_response.status_code == 200
        get1_data = get1_response.json()
        assert len(get1_data["user_commands"]) == 1

        # Create second share with command1 + command2 (command1 is duplicate)
        response2 = requests.post(
            f"{api_client}/api/shares",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "project_name": project_name,
                "stats": {"views": 2},
                "user_commands": [
                    {"timestamp": "2024-01-01T00:00:00", "hash": "cmd1"},  # duplicate
                    {"timestamp": "2024-01-01T00:01:00", "hash": "cmd2"},  # new
                ],
            },
        )
        assert response2.status_code == 200
        data2 = response2.json()

        # Verify uuid is unchanged
        assert data2["uuid"] == uuid

        # Get share to verify commands are merged
        get2_response = requests.get(
            f"{api_client}/api/shares/{uuid}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert get2_response.status_code == 200
        get2_data = get2_response.json()

        # Verify commands are merged (2 unique commands)
        assert len(get2_data["user_commands"]) == 2

        # Verify the commands contain both cmd1 and cmd2
        hashes = {cmd["hash"] for cmd in get2_data["user_commands"]}
        assert hashes == {"cmd1", "cmd2"}


class TestSharesDelete:
    """Test DELETE /api/shares/{uuid}."""

    def test_delete_share(self, docker_services, admin_token, api_client):
        """删除分享返回 200."""
        # Create share
        create_response = requests.post(
            f"{api_client}/api/shares",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "project_name": "delete-test-project",
                "stats": {"views": 3},
                "user_commands": [
                    {"timestamp": "2024-01-01T00:00:00", "hash": "del123"}
                ],
            },
        )
        assert create_response.status_code == 200
        uuid = create_response.json()["uuid"]

        # Delete share
        delete_response = requests.delete(
            f"{api_client}/api/shares/{uuid}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert delete_response.status_code == 200

        # Verify share is gone (404)
        get_response = requests.get(
            f"{api_client}/api/shares/{uuid}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert get_response.status_code == 404
