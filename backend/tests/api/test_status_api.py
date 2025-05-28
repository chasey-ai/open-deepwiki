import pytest
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from backend.app.main import app # The FastAPI application
from backend.app.services.task_service import TaskService
from backend.app.api.status import get_task_service # The dependency override from status.py

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

class TestStatusApiUnit:

    def test_get_task_status_success(self, client: TestClient, mock_task_service: MagicMock):
        task_id = "celery_task_123"
        expected_status_info = {
            "task_id": task_id,
            "status": "SUCCESS",
            "result": {"message": "Task completed successfully"},
            "details": {"progress": 100}
        }
        mock_task_service.get_task_status.return_value = expected_status_info
        
        app.dependency_overrides[get_task_service] = override_get_task_service(mock_task_service)
        
        response = client.get(f"/api/status/{task_id}")
        
        assert response.status_code == 200
        assert response.json() == expected_status_info
        mock_task_service.get_task_status.assert_called_once_with(task_id=task_id)
        
        app.dependency_overrides = {} # Clean up

    def test_get_task_status_pending(self, client: TestClient, mock_task_service: MagicMock):
        task_id = "celery_task_pending"
        expected_status_info = {
            "task_id": task_id,
            "status": "PENDING",
            "result": None,
            "details": None
        }
        mock_task_service.get_task_status.return_value = expected_status_info
        
        app.dependency_overrides[get_task_service] = override_get_task_service(mock_task_service)
        
        response = client.get(f"/api/status/{task_id}")
        
        assert response.status_code == 200
        assert response.json() == expected_status_info
        mock_task_service.get_task_status.assert_called_once_with(task_id=task_id)
        
        app.dependency_overrides = {}

    def test_get_task_status_failure(self, client: TestClient, mock_task_service: MagicMock):
        task_id = "celery_task_failed"
        expected_status_info = {
            "task_id": task_id,
            "status": "FAILURE",
            "result": "Error: Something went wrong",
            "details": {"traceback": "..."}
        }
        mock_task_service.get_task_status.return_value = expected_status_info
        
        app.dependency_overrides[get_task_service] = override_get_task_service(mock_task_service)
        
        response = client.get(f"/api/status/{task_id}")
        
        assert response.status_code == 200 # API returns 200, status is in the body
        assert response.json() == expected_status_info
        mock_task_service.get_task_status.assert_called_once_with(task_id=task_id)
        
        app.dependency_overrides = {}

    def test_get_task_status_service_returns_error_status(self, client: TestClient, mock_task_service: MagicMock):
        # Test case where TaskService itself encounters an issue (e.g., Celery not reachable)
        # and returns a structured error, as per TaskService.get_task_status implementation.
        task_id = "task_celery_unreachable"
        service_error_response = {
            "task_id": task_id,
            "status": "UNKNOWN", # Or "ERROR_FETCHING_STATUS"
            "result": "Celery connection error.", # Example error from TaskService
            "details": None
        }
        mock_task_service.get_task_status.return_value = service_error_response
        
        app.dependency_overrides[get_task_service] = override_get_task_service(mock_task_service)
        
        response = client.get(f"/api/status/{task_id}")
        
        assert response.status_code == 200 # The API endpoint itself is fine
        assert response.json() == service_error_response 
        mock_task_service.get_task_status.assert_called_once_with(task_id=task_id)
        
        app.dependency_overrides = {}

    def test_get_task_status_service_raises_unexpected_exception(self, client: TestClient, mock_task_service: MagicMock):
        # This tests if the endpoint's own try-except block handles unexpected errors from the service.
        task_id = "task_unexpected_error"
        mock_task_service.get_task_status.side_effect = Exception("A very unexpected service error")
        
        app.dependency_overrides[get_task_service] = override_get_task_service(mock_task_service)
        
        response = client.get(f"/api/status/{task_id}")
        
        assert response.status_code == 500 
        assert response.json() == {"detail": "An unexpected error occurred while fetching task status: A very unexpected service error"}
        mock_task_service.get_task_status.assert_called_once_with(task_id=task_id)
        
        app.dependency_overrides = {}

    # FastAPI's path parameter validation usually handles empty task_ids before reaching the endpoint logic.
    # If task_id were optional or had different validation, more tests here would be needed.
    # For example, testing `client.get("/api/status/ ")` (with space) might hit validation
    # depending on Path(...) definition, or if it reaches the service, TaskService might handle it.
    # The current Path definition `task_id: str = Path(..., min_length=1)` should prevent empty.
    
    def test_get_task_status_non_existent_task_id_handled_by_service(self, client: TestClient, mock_task_service: MagicMock):
        # How Celery's AsyncResult behaves for a non-existent task_id can vary.
        # It might return a PENDING state or raise an error.
        # The TaskService is expected to handle this. Let's assume it returns a specific status.
        task_id = "non_existent_task_id_123"
        # Let's say AsyncResult for a non-existent task_id returns status PENDING and None result
        # (this is a common behavior for some backends if the task was never known).
        non_existent_task_status = {
            "task_id": task_id,
            "status": "PENDING", # Or whatever AsyncResult defaults to for unknown tasks
            "result": None,
            "details": None 
        }
        mock_task_service.get_task_status.return_value = non_existent_task_status
        
        app.dependency_overrides[get_task_service] = override_get_task_service(mock_task_service)
        
        response = client.get(f"/api/status/{task_id}")
        
        assert response.status_code == 200
        assert response.json() == non_existent_task_status
        mock_task_service.get_task_status.assert_called_once_with(task_id=task_id)
        
        app.dependency_overrides = {}
