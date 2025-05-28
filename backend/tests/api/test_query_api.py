import pytest
from unittest.mock import MagicMock

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import HttpUrl

from backend.app.main import app # The FastAPI application
from backend.app.services.query_service import QueryService # Dependency
from backend.app.api.query import get_query_service # The dependency override from query.py

# Fixture for the TestClient
@pytest.fixture
def client():
    return TestClient(app)

# Fixture to mock the QueryService
@pytest.fixture
def mock_query_service():
    mock = MagicMock(spec=QueryService)
    return mock

# Override the dependency for the tests
def override_get_query_service(mock_service_to_provide):
    def _override():
        return mock_service_to_provide
    return _override

class TestQueryApiUnit:

    def test_ask_question_success(self, client: TestClient, mock_query_service: MagicMock):
        repo_url_str = "https://github.com/test/repo"
        question_str = "What is this repo about?"
        
        # Expected output from QueryService.answer_question
        service_response_data = {
            "query": question_str,
            "repo_url": repo_url_str,
            "answer": "This repo is about testing.",
            "documents": [
                {"content": "Test document 1", "meta": {"source": "README.md"}},
                {"content": "Test document 2", "meta": {"source": "CONTRIBUTING.md"}}
            ]
        }
        mock_query_service.answer_question.return_value = service_response_data
        
        app.dependency_overrides[get_query_service] = override_get_query_service(mock_query_service)
        
        request_payload = {"repo_url": repo_url_str, "question": question_str}
        response = client.post("/api/query/ask", json=request_payload)
        
        assert response.status_code == 200
        response_json = response.json()
        assert response_json["query"] == question_str
        assert response_json["repo_url"] == repo_url_str # Pydantic model will ensure it's a valid HttpUrl
        assert response_json["answer"] == "This repo is about testing."
        assert len(response_json["documents"]) == 2
        assert response_json["documents"][0]["content"] == "Test document 1"
        
        mock_query_service.answer_question.assert_called_once_with(repo_url=repo_url_str, question=question_str)
        
        app.dependency_overrides = {} # Clean up

    def test_ask_question_service_raises_http_exception(self, client: TestClient, mock_query_service: MagicMock):
        repo_url_str = "https://github.com/test/repo_error"
        question_str = "Why does this fail?"
        
        mock_query_service.answer_question.side_effect = HTTPException(
            status_code=400, detail="Invalid input to service"
        )
        
        app.dependency_overrides[get_query_service] = override_get_query_service(mock_query_service)
        
        request_payload = {"repo_url": repo_url_str, "question": question_str}
        response = client.post("/api/query/ask", json=request_payload)
        
        assert response.status_code == 400
        assert response.json() == {"detail": "Invalid input to service"}
        mock_query_service.answer_question.assert_called_once_with(repo_url=repo_url_str, question=question_str)
        
        app.dependency_overrides = {}

    def test_ask_question_service_raises_unexpected_exception(self, client: TestClient, mock_query_service: MagicMock):
        repo_url_str = "https://github.com/test/repo_unexpected"
        question_str = "What could go wrong?"
        
        mock_query_service.answer_question.side_effect = Exception("Major service malfunction")
        
        app.dependency_overrides[get_query_service] = override_get_query_service(mock_query_service)
        
        request_payload = {"repo_url": repo_url_str, "question": question_str}
        response = client.post("/api/query/ask", json=request_payload)
        
        assert response.status_code == 500
        assert response.json() == {"detail": "An unexpected error occurred while processing the query: Major service malfunction"}
        mock_query_service.answer_question.assert_called_once_with(repo_url=repo_url_str, question=question_str)
        
        app.dependency_overrides = {}

    @pytest.mark.parametrize("payload, expected_detail_substring", [
        ({"repo_url": "not_a_valid_url", "question": "A question"}, "invalid or missing URL scheme"), # Invalid URL
        ({"question": "A question"}, "field required"), # Missing repo_url
        ({"repo_url": "https://github.com/test/repo"}, "field required"), # Missing question
        ({"repo_url": "https://github.com/test/repo", "question": ""}, "ensure this value has at least 1 characters"), # Empty question
    ])
    def test_ask_question_invalid_request_payload(self, client: TestClient, payload, expected_detail_substring):
        # No need to mock service, Pydantic validation happens first
        response = client.post("/api/query/ask", json=payload)
        
        assert response.status_code == 422 # Unprocessable Entity
        # Check if the expected error message part is in any of the error details
        error_details = response.json().get("detail", [])
        assert any(expected_detail_substring in error.get("msg", "") for error in error_details), \
            f"Expected substring '{expected_detail_substring}' not found in error details: {error_details}"

    def test_ask_question_service_returns_empty_documents(self, client: TestClient, mock_query_service: MagicMock):
        repo_url_str = "https://github.com/test/repo_no_docs"
        question_str = "Any docs here?"
        
        service_response_data = {
            "query": question_str,
            "repo_url": repo_url_str,
            "answer": "Found an answer, but no source documents.",
            "documents": [] # Empty list of documents
        }
        mock_query_service.answer_question.return_value = service_response_data
        
        app.dependency_overrides[get_query_service] = override_get_query_service(mock_query_service)
        
        request_payload = {"repo_url": repo_url_str, "question": question_str}
        response = client.post("/api/query/ask", json=request_payload)
        
        assert response.status_code == 200
        response_json = response.json()
        assert response_json["answer"] == "Found an answer, but no source documents."
        assert len(response_json["documents"]) == 0
        
        mock_query_service.answer_question.assert_called_once_with(repo_url=repo_url_str, question=question_str)
        app.dependency_overrides = {}

    def test_ask_question_service_returns_no_answer(self, client: TestClient, mock_query_service: MagicMock):
        repo_url_str = "https://github.com/test/repo_no_answer"
        question_str = "Can you answer this?"
        
        # QueryService might return a specific string when no answer is found
        no_answer_string_from_service = "Sorry, I couldn't find an answer to your question based on the available information."
        service_response_data = {
            "query": question_str,
            "repo_url": repo_url_str,
            "answer": no_answer_string_from_service,
            "documents": [{"content": "Some related document", "meta": {"source": "file.md"}}]
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
