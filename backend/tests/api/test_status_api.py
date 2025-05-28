import pytest
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from backend.app.main import app # FastAPI 应用程序
from backend.app.services.task_service import TaskService
from backend.app.api.status import get_task_service # status.py 中的依赖覆盖

# TestClient 的 Fixture
@pytest.fixture
def client():
    return TestClient(app)

# 用于模拟 TaskService 的 Fixture
@pytest.fixture
def mock_task_service():
    mock = MagicMock(spec=TaskService)
    return mock

# 覆盖测试的依赖项
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
            "result": {"message": "任务已成功完成"},
            "details": {"progress": 100}
        }
        mock_task_service.get_task_status.return_value = expected_status_info
        
        app.dependency_overrides[get_task_service] = override_get_task_service(mock_task_service)
        
        response = client.get(f"/api/status/{task_id}")
        
        assert response.status_code == 200
        assert response.json() == expected_status_info
        mock_task_service.get_task_status.assert_called_once_with(task_id=task_id)
        
        app.dependency_overrides = {} # 清理

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
            "result": "错误：发生了一些问题",
            "details": {"traceback": "..."}
        }
        mock_task_service.get_task_status.return_value = expected_status_info
        
        app.dependency_overrides[get_task_service] = override_get_task_service(mock_task_service)
        
        response = client.get(f"/api/status/{task_id}")
        
        assert response.status_code == 200 # API 返回 200，状态在响应体中
        assert response.json() == expected_status_info
        mock_task_service.get_task_status.assert_called_once_with(task_id=task_id)
        
        app.dependency_overrides = {}

    def test_get_task_status_service_returns_error_status(self, client: TestClient, mock_task_service: MagicMock):
        # 测试 TaskService 本身遇到问题（例如 Celery 无法访问）
        # 并根据 TaskService.get_task_status 实现返回结构化错误的情况。
        task_id = "task_celery_unreachable"
        service_error_response = {
            "task_id": task_id,
            "status": "UNKNOWN", # 或 "ERROR_FETCHING_STATUS"
            "result": "Celery 连接错误。", # TaskService 返回的示例错误
            "details": None
        }
        mock_task_service.get_task_status.return_value = service_error_response
        
        app.dependency_overrides[get_task_service] = override_get_task_service(mock_task_service)
        
        response = client.get(f"/api/status/{task_id}")
        
        assert response.status_code == 200 # API 端点本身是正常的
        assert response.json() == service_error_response 
        mock_task_service.get_task_status.assert_called_once_with(task_id=task_id)
        
        app.dependency_overrides = {}

    def test_get_task_status_service_raises_unexpected_exception(self, client: TestClient, mock_task_service: MagicMock):
        # 此测试检查端点自身的 try-except 块是否处理来自服务的意外错误。
        task_id = "task_unexpected_error"
        mock_task_service.get_task_status.side_effect = Exception("一个非常意外的服务错误")
        
        app.dependency_overrides[get_task_service] = override_get_task_service(mock_task_service)
        
        response = client.get(f"/api/status/{task_id}")
        
        assert response.status_code == 500 
        assert response.json() == {"detail": "获取任务状态时发生意外错误: 一个非常意外的服务错误"}
        mock_task_service.get_task_status.assert_called_once_with(task_id=task_id)
        
        app.dependency_overrides = {}

    # FastAPI 的路径参数验证通常在到达端点逻辑之前处理空 task_id。
    # 如果 task_id 是可选的或具有不同的验证，则此处需要更多测试。
    # 例如，测试 `client.get("/api/status/ ")` (带空格) 可能会触发验证
    # 具体取决于 Path(...) 的定义，或者如果它到达服务，TaskService 可能会处理它。
    # 当前的 Path 定义 `task_id: str = Path(..., min_length=1)` 应阻止空值。
    
    def test_get_task_status_non_existent_task_id_handled_by_service(self, client: TestClient, mock_task_service: MagicMock):
        # Celery 的 AsyncResult 对于不存在的 task_id 的行为可能有所不同。
        # 它可能返回 PENDING 状态或引发错误。
        # TaskService 应处理此情况。我们假设它返回特定状态。
        task_id = "non_existent_task_id_123"
        # 假设对于不存在的 task_id，AsyncResult 返回 PENDING 状态和 None 结果
        # （这对于某些后端来说是常见行为，如果任务从未被知晓）。
        non_existent_task_status = {
            "task_id": task_id,
            "status": "PENDING", # 或 AsyncResult 对未知任务的任何默认值
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
