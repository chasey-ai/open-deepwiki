import pytest
from unittest.mock import MagicMock, patch, ANY

from backend.app.services.task_service import TaskService

# Mock Celery components that TaskService interacts with.
# These would typically be imported from `backend.tasks` or `backend.celery_worker`.
# We patch them where TaskService attempts to import/use them.

# Mock for the Celery task functions
mock_index_repository_task_func = MagicMock(name="index_repository_task_func")
mock_generate_wiki_task_func = MagicMock(name="generate_wiki_task_func")

# Mock for the Celery app instance
mock_celery_app_instance = MagicMock(name="celery_app_instance")

# Mock for AsyncResult
mock_async_result_class = MagicMock(name="AsyncResult_class")


@pytest.fixture
def mock_celery_imports(monkeypatch):
    """Mocks imports that TaskService tries to make for Celery components."""
    monkeypatch.setattr("backend.app.services.task_service.celery_app", mock_celery_app_instance)
    monkeypatch.setattr("backend.app.services.task_service.index_repository_task", mock_index_repository_task_func)
    monkeypatch.setattr("backend.app.services.task_service.generate_wiki_task", mock_generate_wiki_task_func)
    # Also patch AsyncResult where it's used
    monkeypatch.setattr("backend.app.services.task_service.AsyncResult", mock_async_result_class)


@pytest.fixture
def task_service(mock_celery_imports):
    """Provides an instance of TaskService with mocked Celery components."""
    # Reset mocks before each test using this fixture
    mock_index_repository_task_func.reset_mock()
    mock_generate_wiki_task_func.reset_mock()
    mock_celery_app_instance.reset_mock()
    mock_async_result_class.reset_mock()

    # Configure the .apply_async attribute on the mock task functions
    # apply_async should be a callable that returns an object with an 'id' attribute
    mock_index_repository_task_func.apply_async = MagicMock(return_value=MagicMock(id="fake_index_task_id"))
    mock_generate_wiki_task_func.apply_async = MagicMock(return_value=MagicMock(id="fake_wiki_task_id"))
    
    return TaskService()

@pytest.fixture
def task_service_no_celery_app(mock_celery_imports, monkeypatch):
    """Provides TaskService when celery_app is None."""
    monkeypatch.setattr("backend.app.services.task_service.celery_app", None)
    return TaskService()
    
@pytest.fixture
def task_service_no_index_task_func(mock_celery_imports, monkeypatch):
    """Provides TaskService when index_repository_task is None."""
    monkeypatch.setattr("backend.app.services.task_service.index_repository_task", None)
    return TaskService()

@pytest.fixture
def task_service_no_wiki_task_func(mock_celery_imports, monkeypatch):
    """Provides TaskService when generate_wiki_task is None."""
    monkeypatch.setattr("backend.app.services.task_service.generate_wiki_task", None)
    return TaskService()


class TestTaskServiceUnit:

    def test_init_success(self, task_service: TaskService):
        assert task_service is not None
        # (Optional) Check logger critical message not called if celery_app is present
        # This requires capturing logs or more complex mocking of the logger.

    def test_init_no_celery_app_logs_critical(self, caplog):
        # For this test, we don't use the fixture that mocks celery_app to be present.
        # Instead, we want to test the scenario where the import leads to celery_app being None.
        with patch("backend.app.services.task_service.celery_app", None):
            TaskService()
            assert "Celery application (`celery_app`) is not imported or available." in caplog.text
            assert "Task functionality will be disabled." in caplog.text


    # Tests for create_indexing_task
    def test_create_indexing_task_success(self, task_service: TaskService):
        repo_url = "https://github.com/test/repo"
        task_id = task_service.create_indexing_task(repo_url)
        
        assert task_id == "fake_index_task_id"
        mock_index_repository_task_func.apply_async.assert_called_once_with(
            args=(), kwargs={"repo_url": repo_url}
        )

    def test_create_indexing_task_no_celery_app(self, task_service_no_celery_app: TaskService, caplog):
        repo_url = "https://github.com/test/repo"
        task_id = task_service_no_celery_app.create_indexing_task(repo_url)
        
        assert task_id is None
        assert "Cannot dispatch 'repository_indexing'" in caplog.text
        assert "Celery app or task function is unavailable" in caplog.text

    def test_create_indexing_task_no_task_function(self, task_service_no_index_task_func: TaskService, caplog):
        repo_url = "https://github.com/test/repo"
        task_id = task_service_no_index_task_func.create_indexing_task(repo_url)
        
        assert task_id is None
        assert "`index_repository_task` is not available" in caplog.text

    def test_create_indexing_task_apply_async_fails(self, task_service: TaskService, caplog):
        repo_url = "https://github.com/test/repo"
        mock_index_repository_task_func.apply_async.side_effect = Exception("Celery dispatch error")
        
        task_id = task_service.create_indexing_task(repo_url)
        
        assert task_id is None
        assert "Exception during dispatch of 'repository_indexing'" in caplog.text
        assert "Celery dispatch error" in caplog.text


    # Tests for create_wiki_generation_task
    def test_create_wiki_generation_task_success(self, task_service: TaskService):
        repo_url = "https://github.com/test/repo"
        task_id = task_service.create_wiki_generation_task(repo_url)
        
        assert task_id == "fake_wiki_task_id"
        mock_generate_wiki_task_func.apply_async.assert_called_once_with(
            args=(), kwargs={"repo_url": repo_url}
        )

    def test_create_wiki_generation_task_no_celery_app(self, task_service_no_celery_app: TaskService, caplog):
        repo_url = "https://github.com/test/repo"
        task_id = task_service_no_celery_app.create_wiki_generation_task(repo_url)
        assert task_id is None
        assert "Cannot dispatch 'wiki_generation'" in caplog.text

    def test_create_wiki_generation_task_no_task_function(self, task_service_no_wiki_task_func: TaskService, caplog):
        repo_url = "https://github.com/test/repo"
        task_id = task_service_no_wiki_task_func.create_wiki_generation_task(repo_url)
        assert task_id is None
        assert "`generate_wiki_task` is not available" in caplog.text

    def test_create_wiki_generation_task_apply_async_fails(self, task_service: TaskService, caplog):
        repo_url = "https://github.com/test/repo"
        mock_generate_wiki_task_func.apply_async.side_effect = Exception("Celery dispatch error for wiki")
        task_id = task_service.create_wiki_generation_task(repo_url)
        assert task_id is None
        assert "Exception during dispatch of 'wiki_generation'" in caplog.text

    # Tests for get_task_status
    @pytest.mark.parametrize("task_state, task_result, expected_status_str, expected_result_val", [
        ("PENDING", None, "PENDING", None),
        ("STARTED", None, "STARTED", None),
        ("SUCCESS", "Task completed successfully.", "SUCCESS", "Task completed successfully."),
        ("FAILURE", Exception("Task failed badly"), "FAILURE", "Failure: Task failed badly"),
        ("RETRY", None, "RETRY", None), # Assuming result is None for RETRY
    ])
    def test_get_task_status_various_states(self, task_service: TaskService, task_state, task_result, expected_status_str, expected_result_val):
        task_id = "some_task_id"
        
        mock_result_instance = MagicMock()
        mock_result_instance.status = task_state
        mock_result_instance.result = task_result
        mock_result_instance.failed.return_value = (task_state == "FAILURE")
        mock_result_instance.successful.return_value = (task_state == "SUCCESS")
        # mock_result_instance.info = {"progress": 50} # Optional: if you use .info
        
        mock_async_result_class.return_value = mock_result_instance
        
        status_response = task_service.get_task_status(task_id)
        
        mock_async_result_class.assert_called_once_with(task_id, app=mock_celery_app_instance)
        assert status_response["task_id"] == task_id
        assert status_response["status"] == expected_status_str
        assert status_response["result"] == expected_result_val
        # assert status_response["details"] == {"progress": 50} # If .info is used

    def test_get_task_status_no_celery_app(self, task_service_no_celery_app: TaskService, caplog):
        task_id = "some_task_id"
        status_response = task_service_no_celery_app.get_task_status(task_id)
        
        assert status_response["task_id"] == task_id
        assert status_response["status"] == "UNKNOWN"
        assert "Celery connection error" in status_response["result"] # As per TaskService implementation
        assert "Celery app unavailable. Cannot get status for task" in caplog.text

    def test_get_task_status_async_result_exception(self, task_service: TaskService, caplog):
        task_id = "some_task_id"
        mock_async_result_class.side_effect = Exception("AsyncResult internal error")
        
        status_response = task_service.get_task_status(task_id)
        
        assert status_response["task_id"] == task_id
        assert status_response["status"] == "ERROR_FETCHING_STATUS"
        assert "AsyncResult internal error" in status_response["result"]
        assert "Exception while fetching status for task" in caplog.text

    def test_get_task_status_with_details_from_info(self, task_service: TaskService):
        task_id = "task_with_details"
        mock_result_instance = MagicMock()
        mock_result_instance.status = "PROGRESS" # Example status where .info might be relevant
        mock_result_instance.result = None
        mock_result_instance.failed.return_value = False
        mock_result_instance.successful.return_value = False
        mock_result_instance.info = {"custom_progress": "Step 3/5", "percent": 60} # Example .info content
        
        mock_async_result_class.return_value = mock_result_instance
        
        status_response = task_service.get_task_status(task_id)
        
        assert status_response["task_id"] == task_id
        assert status_response["status"] == "PROGRESS"
        assert status_response["result"] is None
        assert status_response["details"] == {"custom_progress": "Step 3/5", "percent": 60}
        mock_async_result_class.assert_called_once_with(task_id, app=mock_celery_app_instance)Okay, I've written the unit tests for `TaskService`. Now I'll proceed to write tests for the `/api/status/{task_id}` API endpoint in `backend/tests/api/test_status_api.py`.

This will involve:
1.  Using `TestClient` from `fastapi.testing`.
2.  Mocking the `TaskService` dependency.
3.  Testing a successful scenario where the service returns task status.
4.  Testing scenarios where `task_id` might be invalid (though FastAPI path validation usually handles this, good to be aware).
5.  Testing how the API behaves if the `TaskService.get_task_status` method itself returns a dictionary indicating an issue (e.g., Celery connection error, as handled in `TaskService`).

I'll create `backend/tests/api/test_status_api.py`.
