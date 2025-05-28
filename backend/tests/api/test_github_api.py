import pytest
from unittest.mock import MagicMock, AsyncMock

from fastapi import HTTPException
from fastapi.testclient import TestClient

# Assuming main.py defines the FastAPI app instance
# and GithubService is the new service used by the /readme endpoint
from backend.app.main import app # The FastAPI application
from backend.app.services.github_service import GithubService as NewGithubService
from backend.app.api.github import get_new_github_service # The dependency override

# Fixture for the TestClient
@pytest.fixture
def client():
    return TestClient(app)

# Fixture to mock the NewGithubService
@pytest.fixture
def mock_github_service():
    mock = MagicMock(spec=NewGithubService) # Use MagicMock for sync methods if any, but service methods are async
    # If all methods are async, AsyncMock might be better, but MagicMock can mock async methods too.
    mock.get_readme_content = AsyncMock() # Explicitly make it an AsyncMock
    return mock

# Override the dependency for the tests
def override_get_new_github_service(mock_service_to_provide):
    def _override():
        return mock_service_to_provide
    return _override

class TestGithubApiUnit:

    def test_get_readme_success(self, client: TestClient, mock_github_service: MagicMock):
        expected_readme_content = "This is a test README."
        mock_github_service.get_readme_content.return_value = expected_readme_content
        
        # Override the dependency to use the mock
        app.dependency_overrides[get_new_github_service] = override_get_new_github_service(mock_github_service)
        
        response = client.post("/api/github/readme", json={"url": "https://github.com/test/repo"})
        
        assert response.status_code == 200
        assert response.text == expected_readme_content
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        mock_github_service.get_readme_content.assert_awaited_once_with("https://github.com/test/repo")
        
        # Clean up dependency override
        app.dependency_overrides = {}

    def test_get_readme_service_raises_http_exception(self, client: TestClient, mock_github_service: MagicMock):
        mock_github_service.get_readme_content.side_effect = HTTPException(
            status_code=404, detail="README not found"
        )
        
        app.dependency_overrides[get_new_github_service] = override_get_new_github_service(mock_github_service)
        
        response = client.post("/api/github/readme", json={"url": "https://github.com/test/repo"})
        
        assert response.status_code == 404
        assert response.json() == {"detail": "README not found"}
        mock_github_service.get_readme_content.assert_awaited_once_with("https://github.com/test/repo")
        
        app.dependency_overrides = {}

    def test_get_readme_service_raises_unexpected_exception(self, client: TestClient, mock_github_service: MagicMock):
        mock_github_service.get_readme_content.side_effect = Exception("Some internal service error")
        
        app.dependency_overrides[get_new_github_service] = override_get_new_github_service(mock_github_service)
        
        response = client.post("/api/github/readme", json={"url": "https://github.com/test/repo"})
        
        assert response.status_code == 500
        assert response.json() == {"detail": "An unexpected error occurred: Some internal service error"}
        mock_github_service.get_readme_content.assert_awaited_once_with("https://github.com/test/repo")
        
        app.dependency_overrides = {}

    def test_get_readme_invalid_request_body_url(self, client: TestClient):
        # No need to mock the service here as validation happens before service call
        response = client.post("/api/github/readme", json={"url": "not_a_valid_url"})
        
        assert response.status_code == 422 # Unprocessable Entity for Pydantic validation errors
        # The exact error message structure can vary slightly with Pydantic versions
        assert "url" in response.json()["detail"][0]["loc"]
        assert "invalid or missing URL scheme" in response.json()["detail"][0]["msg"] or "URL scheme not permitted" in response.json()["detail"][0]["msg"]

    def test_get_readme_missing_url_in_request(self, client: TestClient):
        response = client.post("/api/github/readme", json={"wrong_field": "https://github.com/test/repo"})
        
        assert response.status_code == 422 
        assert "url" in response.json()["detail"][0]["loc"]
        assert "field required" in response.json()["detail"][0]["msg"]

    # Test the deprecated /repository endpoint briefly for existence and basic error if old services are not mocked/available
    # This is more of an integration check that it's still wired up.
    # Actual functionality tests for it would require mocking its specific (old) dependencies.
    def test_deprecated_repository_endpoint_basic_check(self, client: TestClient):
        # This test assumes that `old_github_service_instance` and `old_task_service_instance`
        # as imported in `backend/app/api/github.py` might not be fully functional
        # or might be simple mocks/placeholders in a unit testing context if not specifically set up.
        # We're just checking if the endpoint is reachable and returns some form of error
        # if its unmocked dependencies fail, or a success if they are somehow available.
        # Here, we expect it to fail because its internal services are not mocked for this test suite.
        # Specifically, `old_github_service_instance.validate_repository_url` would be called.
        
        # If `old_github_service_instance` is a MagicMock that hasn't been configured,
        # calling methods on it might work or raise errors depending on MagicMock's default behavior.
        # Let's simulate it raising an AttributeError if not properly configured.
        with patch('backend.app.api.github.old_github_service_instance') as mock_old_service:
            mock_old_service.validate_repository_url.return_value = False # Or raise an error
            
            response = client.post("/api/github/repository", json={"url": "https://github.com/test/repo"})
            
            # If validate_repository_url returns False, it should raise a 400 HTTPException
            assert response.status_code == 400
            assert response.json() == {"detail": "Invalid GitHub repository URL"}

        # Test when validate_repository_url returns True, but extract_repo_info fails
        with patch('backend.app.api.github.old_github_service_instance') as mock_old_service, \
             patch('backend.app.api.github.old_task_service_instance') as mock_old_task_service: # Mock this too
            mock_old_service.validate_repository_url.return_value = True
            mock_old_service.extract_repo_info.side_effect = ValueError("Mocked extraction error")
            
            response = client.post("/api/github/repository", json={"url": "https://github.com/test/repo"})
            
            assert response.status_code == 400
            assert response.json() == {"detail": "Mocked extraction error"}

        # Test when extract_repo_info succeeds but create_task fails
        with patch('backend.app.api.github.old_github_service_instance') as mock_old_service, \
             patch('backend.app.api.github.old_task_service_instance') as mock_old_task_service:
            mock_old_service.validate_repository_url.return_value = True
            mock_old_service.extract_repo_info.return_value = {"id": "test_id", "url": "https://github.com/test/repo", "name": "repo", "owner": "test"}
            mock_old_task_service.create_task.side_effect = Exception("Mocked task creation error")
            
            response = client.post("/api/github/repository", json={"url": "https://github.com/test/repo"})
            
            assert response.status_code == 500 # It's caught by a generic Exception handler
            assert "Server error: Mocked task creation error" in response.json()["detail"]

    # Test successful path for deprecated endpoint (requires more mocking)
    def test_deprecated_repository_endpoint_success(self, client: TestClient):
        with patch('backend.app.api.github.old_github_service_instance') as mock_old_gh_service, \
             patch('backend.app.api.github.old_task_service_instance') as mock_old_task_service:
            
            mock_old_gh_service.validate_repository_url.return_value = True
            mock_repo_info = {"id": "testuser_testrepo", "url": "https://github.com/testuser/testrepo", "name": "testrepo", "owner": "testuser", "description": "A test repo"}
            mock_old_gh_service.extract_repo_info.return_value = mock_repo_info
            
            mock_task_info = {"id": "task_123", "status": "pending", "message": "Task created"}
            mock_old_task_service.create_task.return_value = mock_task_info
            
            response = client.post("/api/github/repository", json={"url": "https://github.com/testuser/testrepo"})
            
            assert response.status_code == 200
            expected_response_data = {
                **mock_repo_info,
                "task_id": mock_task_info["id"],
                "status": mock_task_info["status"],
                "message": mock_task_info["message"]
            }
            assert response.json() == expected_response_data
            mock_old_gh_service.validate_repository_url.assert_called_once_with("https://github.com/testuser/testrepo")
            mock_old_gh_service.extract_repo_info.assert_called_once_with("https://github.com/testuser/testrepo")
            mock_old_task_service.create_task.assert_called_once_with("index", "testuser_testrepo")
