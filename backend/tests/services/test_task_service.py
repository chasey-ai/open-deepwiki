import pytest
from unittest.mock import MagicMock, patch, ANY

from backend.app.services.task_service import TaskService

# 模拟 TaskService 交互的 Celery 组件。
# 这些通常会从 `backend.tasks` 或 `backend.celery_worker` 导入。
# 我们在 TaskService 尝试导入/使用它们的地方对它们进行修补。

# Celery 任务函数的模拟对象
mock_index_repository_task_func = MagicMock(name="index_repository_task_func")
mock_generate_wiki_task_func = MagicMock(name="generate_wiki_task_func")

# Celery 应用实例的模拟对象
mock_celery_app_instance = MagicMock(name="celery_app_instance")

# AsyncResult 的模拟对象
mock_async_result_class = MagicMock(name="AsyncResult_class")


@pytest.fixture
def mock_celery_imports(monkeypatch):
    """模拟 TaskService 尝试为 Celery 组件进行的导入。"""
    monkeypatch.setattr("backend.app.services.task_service.celery_app", mock_celery_app_instance)
    monkeypatch.setattr("backend.app.services.task_service.index_repository_task", mock_index_repository_task_func)
    monkeypatch.setattr("backend.app.services.task_service.generate_wiki_task", mock_generate_wiki_task_func)
    # 同时修补 AsyncResult 使用的地方
    monkeypatch.setattr("backend.app.services.task_service.AsyncResult", mock_async_result_class)


@pytest.fixture
def task_service(mock_celery_imports):
    """提供一个带有模拟 Celery 组件的 TaskService 实例。"""
    # 在使用此 fixture 的每个测试之前重置模拟对象
    mock_index_repository_task_func.reset_mock()
    mock_generate_wiki_task_func.reset_mock()
    mock_celery_app_instance.reset_mock()
    mock_async_result_class.reset_mock()

    # 在模拟任务函数上配置 .apply_async 属性
    # apply_async 应该是一个可调用对象，返回一个具有 'id' 属性的对象
    mock_index_repository_task_func.apply_async = MagicMock(return_value=MagicMock(id="fake_index_task_id"))
    mock_generate_wiki_task_func.apply_async = MagicMock(return_value=MagicMock(id="fake_wiki_task_id"))
    
    return TaskService()

@pytest.fixture
def task_service_no_celery_app(mock_celery_imports, monkeypatch):
    """当 celery_app 为 None 时提供 TaskService。"""
    monkeypatch.setattr("backend.app.services.task_service.celery_app", None)
    return TaskService()
    
@pytest.fixture
def task_service_no_index_task_func(mock_celery_imports, monkeypatch):
    """当 index_repository_task 为 None 时提供 TaskService。"""
    monkeypatch.setattr("backend.app.services.task_service.index_repository_task", None)
    return TaskService()

@pytest.fixture
def task_service_no_wiki_task_func(mock_celery_imports, monkeypatch):
    """当 generate_wiki_task 为 None 时提供 TaskService。"""
    monkeypatch.setattr("backend.app.services.task_service.generate_wiki_task", None)
    return TaskService()


class TestTaskServiceUnit:

    def test_init_success(self, task_service: TaskService):
        assert task_service is not None
        # (可选) 如果 celery_app 存在，检查 logger critical 消息是否未被调用
        # 这需要捕获日志或更复杂的记录器模拟。

    def test_init_no_celery_app_logs_critical(self, caplog):
        # 对于此测试，我们不使用模拟 celery_app 存在的 fixture。
        # 相反，我们想测试导入导致 celery_app 为 None 的场景。
        with patch("backend.app.services.task_service.celery_app", None):
            TaskService()
            assert "Celery 应用 (`celery_app`) 未导入或不可用。" in caplog.text # "Celery application (`celery_app`) is not imported or available."
            assert "任务功能将被禁用。" in caplog.text # "Task functionality will be disabled."


    # create_indexing_task 的测试
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
        assert "无法分派 'repository_indexing'" in caplog.text # "Cannot dispatch 'repository_indexing'"
        assert "Celery 应用或任务函数不可用" in caplog.text # "Celery app or task function is unavailable"

    def test_create_indexing_task_no_task_function(self, task_service_no_index_task_func: TaskService, caplog):
        repo_url = "https://github.com/test/repo"
        task_id = task_service_no_index_task_func.create_indexing_task(repo_url)
        
        assert task_id is None
        assert "`index_repository_task` 不可用" in caplog.text # "`index_repository_task` is not available"

    def test_create_indexing_task_apply_async_fails(self, task_service: TaskService, caplog):
        repo_url = "https://github.com/test/repo"
        mock_index_repository_task_func.apply_async.side_effect = Exception("Celery 分派错误")
        
        task_id = task_service.create_indexing_task(repo_url)
        
        assert task_id is None
        assert "分派 'repository_indexing' 期间发生异常" in caplog.text # "Exception during dispatch of 'repository_indexing'"
        assert "Celery 分派错误" in caplog.text # "Celery dispatch error"


    # create_wiki_generation_task 的测试
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
        assert "无法分派 'wiki_generation'" in caplog.text # "Cannot dispatch 'wiki_generation'"

    def test_create_wiki_generation_task_no_task_function(self, task_service_no_wiki_task_func: TaskService, caplog):
        repo_url = "https://github.com/test/repo"
        task_id = task_service_no_wiki_task_func.create_wiki_generation_task(repo_url)
        assert task_id is None
        assert "`generate_wiki_task` 不可用" in caplog.text # "`generate_wiki_task` is not available"

    def test_create_wiki_generation_task_apply_async_fails(self, task_service: TaskService, caplog):
        repo_url = "https://github.com/test/repo"
        mock_generate_wiki_task_func.apply_async.side_effect = Exception("wiki 的 Celery 分派错误")
        task_id = task_service.create_wiki_generation_task(repo_url)
        assert task_id is None
        assert "分派 'wiki_generation' 期间发生异常" in caplog.text # "Exception during dispatch of 'wiki_generation'"

    # get_task_status 的测试
    @pytest.mark.parametrize("task_state, task_result, expected_status_str, expected_result_val", [
        ("PENDING", None, "PENDING", None),
        ("STARTED", None, "STARTED", None),
        ("SUCCESS", "任务已成功完成。", "SUCCESS", "任务已成功完成。"), # "Task completed successfully."
        ("FAILURE", Exception("任务严重失败"), "FAILURE", "失败: 任务严重失败"), # "Failure: Task failed badly"
        ("RETRY", None, "RETRY", None), # 假设 RETRY 的结果为 None
    ])
    def test_get_task_status_various_states(self, task_service: TaskService, task_state, task_result, expected_status_str, expected_result_val):
        task_id = "some_task_id"
        
        mock_result_instance = MagicMock()
        mock_result_instance.status = task_state
        mock_result_instance.result = task_result
        mock_result_instance.failed.return_value = (task_state == "FAILURE")
        mock_result_instance.successful.return_value = (task_state == "SUCCESS")
        # mock_result_instance.info = {"progress": 50} # 可选：如果使用 .info
        
        mock_async_result_class.return_value = mock_result_instance
        
        status_response = task_service.get_task_status(task_id)
        
        mock_async_result_class.assert_called_once_with(task_id, app=mock_celery_app_instance)
        assert status_response["task_id"] == task_id
        assert status_response["status"] == expected_status_str
        assert status_response["result"] == expected_result_val
        # assert status_response["details"] == {"progress": 50} # 如果使用 .info

    def test_get_task_status_no_celery_app(self, task_service_no_celery_app: TaskService, caplog):
        task_id = "some_task_id"
        status_response = task_service_no_celery_app.get_task_status(task_id)
        
        assert status_response["task_id"] == task_id
        assert status_response["status"] == "UNKNOWN"
        assert "Celery 连接错误" in status_response["result"] # 根据 TaskService 实现 # "Celery connection error"
        assert "Celery 应用不可用。无法获取任务" in caplog.text # "Celery app unavailable. Cannot get status for task"

    def test_get_task_status_async_result_exception(self, task_service: TaskService, caplog):
        task_id = "some_task_id"
        mock_async_result_class.side_effect = Exception("AsyncResult 内部错误")
        
        status_response = task_service.get_task_status(task_id)
        
        assert status_response["task_id"] == task_id
        assert status_response["status"] == "ERROR_FETCHING_STATUS"
        assert "AsyncResult 内部错误" in status_response["result"] # "AsyncResult internal error"
        assert "获取任务状态时发生异常" in caplog.text # "Exception while fetching status for task"

    def test_get_task_status_with_details_from_info(self, task_service: TaskService):
        task_id = "task_with_details"
        mock_result_instance = MagicMock()
        mock_result_instance.status = "PROGRESS" # .info 可能相关的示例状态
        mock_result_instance.result = None
        mock_result_instance.failed.return_value = False
        mock_result_instance.successful.return_value = False
        mock_result_instance.info = {"custom_progress": "步骤 3/5", "percent": 60} # 示例 .info 内容
        
        mock_async_result_class.return_value = mock_result_instance
        
        status_response = task_service.get_task_status(task_id)
        
        assert status_response["task_id"] == task_id
        assert status_response["status"] == "PROGRESS"
        assert status_response["result"] is None
        assert status_response["details"] == {"custom_progress": "步骤 3/5", "percent": 60}
        mock_async_result_class.assert_called_once_with(task_id, app=mock_celery_app_instance)
