import pytest
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from backend.app.main import app # The FastAPI application
from backend.app.services.task_service import TaskService # Dependency of the endpoint
from backend.app.api.wiki import get_task_service # The dependency override from wiki.py

# Fixture for the TestClient
@pytest.fixture
def client():
    return TestClient(app)

# Fixture to mock the TaskService
@pytest.fixture
def mock_task_service():
    mock = MagicMock(spec=TaskService)
    return mock

# Override the dependency for the tests
def override_get_task_service(mock_service_to_provide):
    def _override():
        return mock_service_to_provide
    return _override

class TestWikiApiUnit:

    def test_trigger_wiki_generation_success(self, client: TestClient, mock_task_service: MagicMock):
        repo_url = "https://github.com/test/repo"
        expected_task_id = "fake_wiki_task_id_123"
        
        mock_task_service.create_wiki_generation_task.return_value = expected_task_id
        
        app.dependency_overrides[get_task_service] = override_get_task_service(mock_task_service)
        
        response = client.post("/api/wiki/generate", json={"url": repo_url})
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["task_id"] == expected_task_id
        assert response_data["message"] == "Wiki generation task successfully created."
        assert response_data["repo_url"] == repo_url
        
        mock_task_service.create_wiki_generation_task.assert_called_once_with(repo_url=repo_url)
        
        app.dependency_overrides = {} # Clean up

    def test_trigger_wiki_generation_task_creation_fails(self, client: TestClient, mock_task_service: MagicMock):
        repo_url = "https://github.com/test/repo_fail"
        
        # Simulate TaskService failing to create a task (e.g., Celery issue)
        mock_task_service.create_wiki_generation_task.return_value = None 
        
        app.dependency_overrides[get_task_service] = override_get_task_service(mock_task_service)
        
        response = client.post("/api/wiki/generate", json={"url": repo_url})
        
        assert response.status_code == 500
        assert "Failed to create wiki generation task" in response.json()["detail"]
        assert repo_url in response.json()["detail"]
        
        mock_task_service.create_wiki_generation_task.assert_called_once_with(repo_url=repo_url)
        
        app.dependency_overrides = {}

    def test_trigger_wiki_generation_invalid_url(self, client: TestClient):
        # No need to mock service as Pydantic validation should catch this.
        response = client.post("/api/wiki/generate", json={"url": "not_a_valid_http_url"})
        
        assert response.status_code == 422 # Unprocessable Entity
        assert "url" in response.json()["detail"][0]["loc"]
        # Pydantic error messages can vary slightly
        assert "invalid or missing URL scheme" in response.json()["detail"][0]["msg"] or \
               "URL scheme not permitted" in response.json()["detail"][0]["msg"]

    def test_trigger_wiki_generation_missing_url(self, client: TestClient):
        response = client.post("/api/wiki/generate", json={"repo_url": "https://github.com/test/repo"}) # Incorrect field name
        
        assert response.status_code == 422
        assert "url" in response.json()["detail"][0]["loc"]
        assert "field required" in response.json()["detail"][0]["msg"]

    # Test the deprecated GET /{repo_id} endpoint for basic behavior
    def test_deprecated_get_wiki_content_mock(self, client: TestClient):
        # This endpoint is marked as deprecated and raises a 501 Not Implemented
        response = client.get("/api/wiki/some_repo_id")
        
        assert response.status_code == 501
        assert "Fetching wiki content by repo_id is not fully implemented" in response.json()["detail"]
