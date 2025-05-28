import pytest
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from backend.app.main import app # FastAPI 应用程序
from backend.app.services.task_service import TaskService # 端点的依赖项
from backend.app.api.wiki import get_task_service # wiki.py 中的依赖覆盖

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
        assert response_data["message"] == "Wiki 生成任务已成功创建。"
        assert response_data["repo_url"] == repo_url
        
        mock_task_service.create_wiki_generation_task.assert_called_once_with(repo_url=repo_url)
        
        app.dependency_overrides = {} # 清理

    def test_trigger_wiki_generation_task_creation_fails(self, client: TestClient, mock_task_service: MagicMock):
        repo_url = "https://github.com/test/repo_fail"
        
        # 模拟 TaskService 创建任务失败 (例如 Celery 问题)
        mock_task_service.create_wiki_generation_task.return_value = None 
        
        app.dependency_overrides[get_task_service] = override_get_task_service(mock_task_service)
        
        response = client.post("/api/wiki/generate", json={"url": repo_url})
        
        assert response.status_code == 500
        assert "创建 wiki 生成任务失败" in response.json()["detail"] # "Failed to create wiki generation task"
        assert repo_url in response.json()["detail"]
        
        mock_task_service.create_wiki_generation_task.assert_called_once_with(repo_url=repo_url)
        
        app.dependency_overrides = {}

    def test_trigger_wiki_generation_invalid_url(self, client: TestClient):
        # 无需模拟服务，因为 Pydantic 验证会捕获此问题。
        response = client.post("/api/wiki/generate", json={"url": "not_a_valid_http_url"})
        
        assert response.status_code == 422 # 不可处理的实体
        assert "url" in response.json()["detail"][0]["loc"]
        # Pydantic 错误消息可能略有不同
        assert "invalid or missing URL scheme" in response.json()["detail"][0]["msg"] or \
               "URL scheme not permitted" in response.json()["detail"][0]["msg"]

    def test_trigger_wiki_generation_missing_url(self, client: TestClient):
        response = client.post("/api/wiki/generate", json={"repo_url": "https://github.com/test/repo"}) # 字段名称不正确
        
        assert response.status_code == 422
        assert "url" in response.json()["detail"][0]["loc"]
        assert "field required" in response.json()["detail"][0]["msg"]

    # 测试已弃用的 GET /{repo_id} 端点的基本行为
    def test_deprecated_get_wiki_content_mock(self, client: TestClient):
        # 此端点已标记为已弃用，并引发 501 Not Implemented 错误
        response = client.get("/api/wiki/some_repo_id")
        
        assert response.status_code == 501
        assert "通过 repo_id 获取 wiki 内容的功能尚未使用新服务完全实现" in response.json()["detail"] # "Fetching wiki content by repo_id is not fully implemented"
