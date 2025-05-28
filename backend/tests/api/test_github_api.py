import pytest
from unittest.mock import MagicMock, AsyncMock

from fastapi import HTTPException
from fastapi.testclient import TestClient

# 假设 main.py 定义了 FastAPI 应用实例
# 并且 GithubService 是 /readme 端点使用的新服务
from backend.app.main import app # FastAPI 应用程序
from backend.app.services.github_service import GithubService as NewGithubService
from backend.app.api.github import get_new_github_service # 依赖覆盖

# TestClient 的 Fixture
@pytest.fixture
def client():
    return TestClient(app)

# 用于模拟 NewGithubService 的 Fixture
@pytest.fixture
def mock_github_service():
    mock = MagicMock(spec=NewGithubService) # 如果有同步方法，则使用 MagicMock，但服务方法是异步的
    # 如果所有方法都是异步的，AsyncMock 可能更好，但 MagicMock 也可以模拟异步方法。
    mock.get_readme_content = AsyncMock() # 明确将其设为 AsyncMock
    return mock

# 覆盖测试的依赖项
def override_get_new_github_service(mock_service_to_provide):
    def _override():
        return mock_service_to_provide
    return _override

class TestGithubApiUnit:

    def test_get_readme_success(self, client: TestClient, mock_github_service: MagicMock):
        expected_readme_content = "这是一个测试 README。"
        mock_github_service.get_readme_content.return_value = expected_readme_content
        
        # 覆盖依赖项以使用模拟对象
        app.dependency_overrides[get_new_github_service] = override_get_new_github_service(mock_github_service)
        
        response = client.post("/api/github/readme", json={"url": "https://github.com/test/repo"})
        
        assert response.status_code == 200
        assert response.text == expected_readme_content
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        mock_github_service.get_readme_content.assert_awaited_once_with("https://github.com/test/repo")
        
        # 清理依赖覆盖
        app.dependency_overrides = {}

    def test_get_readme_service_raises_http_exception(self, client: TestClient, mock_github_service: MagicMock):
        mock_github_service.get_readme_content.side_effect = HTTPException(
            status_code=404, detail="未找到 README"
        )
        
        app.dependency_overrides[get_new_github_service] = override_get_new_github_service(mock_github_service)
        
        response = client.post("/api/github/readme", json={"url": "https://github.com/test/repo"})
        
        assert response.status_code == 404
        assert response.json() == {"detail": "未找到 README"}
        mock_github_service.get_readme_content.assert_awaited_once_with("https://github.com/test/repo")
        
        app.dependency_overrides = {}

    def test_get_readme_service_raises_unexpected_exception(self, client: TestClient, mock_github_service: MagicMock):
        mock_github_service.get_readme_content.side_effect = Exception("某些内部服务错误")
        
        app.dependency_overrides[get_new_github_service] = override_get_new_github_service(mock_github_service)
        
        response = client.post("/api/github/readme", json={"url": "https://github.com/test/repo"})
        
        assert response.status_code == 500
        assert response.json() == {"detail": "发生意外错误: 某些内部服务错误"}
        mock_github_service.get_readme_content.assert_awaited_once_with("https://github.com/test/repo")
        
        app.dependency_overrides = {}

    def test_get_readme_invalid_request_body_url(self, client: TestClient):
        # 此处无需模拟服务，因为验证发生在服务调用之前
        response = client.post("/api/github/readme", json={"url": "not_a_valid_url"})
        
        assert response.status_code == 422 # Pydantic 验证错误的不可处理实体
        # 确切的错误消息结构可能因 Pydantic 版本而略有不同
        assert "url" in response.json()["detail"][0]["loc"]
        assert "invalid or missing URL scheme" in response.json()["detail"][0]["msg"] or "URL scheme not permitted" in response.json()["detail"][0]["msg"]

    def test_get_readme_missing_url_in_request(self, client: TestClient):
        response = client.post("/api/github/readme", json={"wrong_field": "https://github.com/test/repo"})
        
        assert response.status_code == 422 
        assert "url" in response.json()["detail"][0]["loc"]
        assert "field required" in response.json()["detail"][0]["msg"]

    # 简要测试已弃用的 /repository 端点的存在性和基本错误（如果未模拟/可用旧服务）
    # 这更像是一个集成检查，检查它是否仍然连接。
    # 其功能测试将需要模拟其特定的（旧）依赖项。
    def test_deprecated_repository_endpoint_basic_check(self, client: TestClient):
        # 此测试假设 `old_github_service_instance` 和 `old_task_service_instance`
        # （在 `backend/app/api/github.py` 中导入）可能无法完全正常工作
        # 或者在单元测试上下文中（如果未专门设置）可能是简单的模拟/占位符。
        # 我们只是检查端点是否可达，并且在其未模拟的依赖项失败时是否返回某种形式的错误，
        # 或者如果它们以某种方式可用，则返回成功。
        # 在这里，我们期望它会失败，因为此测试套件未模拟其内部服务。
        # 具体来说，将调用 `old_github_service_instance.validate_repository_url`。
        
        # 如果 `old_github_service_instance` 是一个未配置的 MagicMock，
        # 调用其方法可能会起作用或引发错误，具体取决于 MagicMock 的默认行为。
        # 如果未正确配置，我们模拟它引发 AttributeError。
        with patch('backend.app.api.github.old_github_service_instance') as mock_old_service:
            mock_old_service.validate_repository_url.return_value = False # 或引发错误
            
            response = client.post("/api/github/repository", json={"url": "https://github.com/test/repo"})
            
            # 如果 validate_repository_url 返回 False，则应引发 400 HTTPException
            assert response.status_code == 400
            assert response.json() == {"detail": "Invalid GitHub repository URL"}

        # 测试 validate_repository_url 返回 True，但 extract_repo_info 失败的情况
        with patch('backend.app.api.github.old_github_service_instance') as mock_old_service, \
             patch('backend.app.api.github.old_task_service_instance') as mock_old_task_service: # 也模拟这个
            mock_old_service.validate_repository_url.return_value = True
            mock_old_service.extract_repo_info.side_effect = ValueError("模拟的提取错误")
            
            response = client.post("/api/github/repository", json={"url": "https://github.com/test/repo"})
            
            assert response.status_code == 400
            assert response.json() == {"detail": "模拟的提取错误"}

        # 测试 extract_repo_info 成功但 create_task 失败的情况
        with patch('backend.app.api.github.old_github_service_instance') as mock_old_service, \
             patch('backend.app.api.github.old_task_service_instance') as mock_old_task_service:
            mock_old_service.validate_repository_url.return_value = True
            mock_old_service.extract_repo_info.return_value = {"id": "test_id", "url": "https://github.com/test/repo", "name": "repo", "owner": "test"}
            mock_old_task_service.create_task.side_effect = Exception("模拟的任务创建错误")
            
            response = client.post("/api/github/repository", json={"url": "https://github.com/test/repo"})
            
            assert response.status_code == 500 # 它被一个通用的 Exception 处理程序捕获
            assert "Server error: Mocked task creation error" in response.json()["detail"]

    # 测试已弃用端点的成功路径 (需要更多模拟)
    def test_deprecated_repository_endpoint_success(self, client: TestClient):
        with patch('backend.app.api.github.old_github_service_instance') as mock_old_gh_service, \
             patch('backend.app.api.github.old_task_service_instance') as mock_old_task_service:
            
            mock_old_gh_service.validate_repository_url.return_value = True
            mock_repo_info = {"id": "testuser_testrepo", "url": "https://github.com/testuser/testrepo", "name": "testrepo", "owner": "testuser", "description": "一个测试仓库"}
            mock_old_gh_service.extract_repo_info.return_value = mock_repo_info
            
            mock_task_info = {"id": "task_123", "status": "pending", "message": "任务已创建"}
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
