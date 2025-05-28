import pytest
from unittest.mock import MagicMock

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import HttpUrl

from backend.app.main import app # FastAPI 应用程序
from backend.app.services.query_service import QueryService # 依赖项
from backend.app.api.query import get_query_service # query.py 中的依赖覆盖

# TestClient 的 Fixture
@pytest.fixture
def client():
    return TestClient(app)

# 用于模拟 QueryService 的 Fixture
@pytest.fixture
def mock_query_service():
    mock = MagicMock(spec=QueryService)
    return mock

# 覆盖测试的依赖项
def override_get_query_service(mock_service_to_provide):
    def _override():
        return mock_service_to_provide
    return _override

class TestQueryApiUnit:

    def test_ask_question_success(self, client: TestClient, mock_query_service: MagicMock):
        repo_url_str = "https://github.com/test/repo"
        question_str = "这个仓库是关于什么的？"
        
        # QueryService.answer_question 的预期输出
        service_response_data = {
            "query": question_str,
            "repo_url": repo_url_str,
            "answer": "这个仓库是关于测试的。",
            "documents": [
                {"content": "测试文档1", "meta": {"source": "README.md"}},
                {"content": "测试文档2", "meta": {"source": "CONTRIBUTING.md"}}
            ]
        }
        mock_query_service.answer_question.return_value = service_response_data
        
        app.dependency_overrides[get_query_service] = override_get_query_service(mock_query_service)
        
        request_payload = {"repo_url": repo_url_str, "question": question_str}
        response = client.post("/api/query/ask", json=request_payload)
        
        assert response.status_code == 200
        response_json = response.json()
        assert response_json["query"] == question_str
        assert response_json["repo_url"] == repo_url_str # Pydantic 模型将确保它是一个有效的 HttpUrl
        assert response_json["answer"] == "这个仓库是关于测试的。"
        assert len(response_json["documents"]) == 2
        assert response_json["documents"][0]["content"] == "测试文档1"
        
        mock_query_service.answer_question.assert_called_once_with(repo_url=repo_url_str, question=question_str)
        
        app.dependency_overrides = {} # 清理

    def test_ask_question_service_raises_http_exception(self, client: TestClient, mock_query_service: MagicMock):
        repo_url_str = "https://github.com/test/repo_error"
        question_str = "为什么这个会失败？"
        
        mock_query_service.answer_question.side_effect = HTTPException(
            status_code=400, detail="服务输入无效"
        )
        
        app.dependency_overrides[get_query_service] = override_get_query_service(mock_query_service)
        
        request_payload = {"repo_url": repo_url_str, "question": question_str}
        response = client.post("/api/query/ask", json=request_payload)
        
        assert response.status_code == 400
        assert response.json() == {"detail": "服务输入无效"}
        mock_query_service.answer_question.assert_called_once_with(repo_url=repo_url_str, question=question_str)
        
        app.dependency_overrides = {}

    def test_ask_question_service_raises_unexpected_exception(self, client: TestClient, mock_query_service: MagicMock):
        repo_url_str = "https://github.com/test/repo_unexpected"
        question_str = "可能会出什么问题？"
        
        mock_query_service.answer_question.side_effect = Exception("严重的服务故障")
        
        app.dependency_overrides[get_query_service] = override_get_query_service(mock_query_service)
        
        request_payload = {"repo_url": repo_url_str, "question": question_str}
        response = client.post("/api/query/ask", json=request_payload)
        
        assert response.status_code == 500
        assert response.json() == {"detail": "处理查询时发生意外错误: 严重的服务故障"}
        mock_query_service.answer_question.assert_called_once_with(repo_url=repo_url_str, question=question_str)
        
        app.dependency_overrides = {}

    @pytest.mark.parametrize("payload, expected_detail_substring", [
        ({"repo_url": "not_a_valid_url", "question": "一个问题"}, "invalid or missing URL scheme"), # 无效的 URL
        ({"question": "一个问题"}, "field required"), # 缺少 repo_url
        ({"repo_url": "https://github.com/test/repo"}, "field required"), # 缺少 question
        ({"repo_url": "https://github.com/test/repo", "question": ""}, "ensure this value has at least 1 characters"), # 空问题
    ])
    def test_ask_question_invalid_request_payload(self, client: TestClient, payload, expected_detail_substring):
        # 无需模拟服务，Pydantic 验证首先发生
        response = client.post("/api/query/ask", json=payload)
        
        assert response.status_code == 422 # 不可处理的实体
        # 检查预期的错误消息部分是否存在于任何错误详细信息中
        error_details = response.json().get("detail", [])
        assert any(expected_detail_substring in error.get("msg", "") for error in error_details), \
            f"在错误详细信息中未找到预期的子字符串 '{expected_detail_substring}': {error_details}"

    def test_ask_question_service_returns_empty_documents(self, client: TestClient, mock_query_service: MagicMock):
        repo_url_str = "https://github.com/test/repo_no_docs"
        question_str = "这里有文档吗？"
        
        service_response_data = {
            "query": question_str,
            "repo_url": repo_url_str,
            "answer": "找到了答案，但没有源文档。",
            "documents": [] # 空的文档列表
        }
        mock_query_service.answer_question.return_value = service_response_data
        
        app.dependency_overrides[get_query_service] = override_get_query_service(mock_query_service)
        
        request_payload = {"repo_url": repo_url_str, "question": question_str}
        response = client.post("/api/query/ask", json=request_payload)
        
        assert response.status_code == 200
        response_json = response.json()
        assert response_json["answer"] == "找到了答案，但没有源文档。"
        assert len(response_json["documents"]) == 0
        
        mock_query_service.answer_question.assert_called_once_with(repo_url=repo_url_str, question=question_str)
        app.dependency_overrides = {}

    def test_ask_question_service_returns_no_answer(self, client: TestClient, mock_query_service: MagicMock):
        repo_url_str = "https://github.com/test/repo_no_answer"
        question_str = "你能回答这个问题吗？"
        
        # QueryService 在找不到答案时可能会返回特定的字符串
        no_answer_string_from_service = "抱歉，根据可用信息，我找不到您问题的答案。"
        service_response_data = {
            "query": question_str,
            "repo_url": repo_url_str,
            "answer": no_answer_string_from_service,
            "documents": [{"content": "一些相关文档", "meta": {"source": "file.md"}}]
        }
        mock_query_service.answer_question.return_value = service_response_data
        
        app.dependency_overrides[get_query_service] = override_get_query_service(mock_query_service)
        
        request_payload = {"repo_url": repo_url_str, "question": question_str}
        response = client.post("/api/query/ask", json=request_payload)
        
        assert response.status_code == 200
        response_json = response.json()
        assert response_json["answer"] == no_answer_string_from_service
        assert len(response_json["documents"]) == 1
        
        mock_query_service.answer_question.assert_called_once_with(repo_url=repo_url_str, question=question_str)
        app.dependency_overrides = {}
