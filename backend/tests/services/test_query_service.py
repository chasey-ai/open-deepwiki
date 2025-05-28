import pytest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from backend.app.services.query_service import QueryService
from haystack.document_stores import BaseDocumentStore # For type hint
from haystack.schema import Document as HaystackDocument # For creating test documents

# Mock for QueryPipeline class/instance
@pytest.fixture
def mock_query_pipeline_instance():
    mock = MagicMock() 
    mock.run = MagicMock() # run method
    return mock

@pytest.fixture
def mock_query_pipeline_class(mock_query_pipeline_instance):
    mock_class = MagicMock()
    mock_class.return_value = mock_query_pipeline_instance
    return mock_class

@pytest.fixture
def mock_document_store():
    return MagicMock(spec=BaseDocumentStore)


class TestQueryServiceUnit:

    def test_query_service_init_success(self, mock_query_pipeline_class, mock_document_store, caplog):
        with patch('agents.pipelines.query_pipeline.QueryPipeline', new=mock_query_pipeline_class):
            service = QueryService(document_store=mock_document_store)
            assert service.query_pipeline == mock_query_pipeline_class.return_value
            # Check if QueryPipeline was called with the document_store
            mock_query_pipeline_class.assert_called_once_with(document_store=mock_document_store)
            assert "QueryService: QueryPipeline initialized successfully." in caplog.text

    def test_query_service_init_pipeline_fails(self, mock_query_pipeline_class, mock_document_store, caplog):
        mock_query_pipeline_class.side_effect = Exception("Pipeline init error")
        with patch('agents.pipelines.query_pipeline.QueryPipeline', new=mock_query_pipeline_class):
            with pytest.raises(RuntimeError) as excinfo:
                QueryService(document_store=mock_document_store)
            assert "QueryService: Failed to initialize QueryPipeline: Pipeline init error" in str(excinfo.value)
            assert "QueryService: Critical error during QueryPipeline initialization." in caplog.text

    # Tests for answer_question
    def test_answer_question_success(self, mock_query_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        question = "What is this project?"
        
        # Mock pipeline output
        mock_answer = "This project is a test."
        mock_doc_content = "Document content related to the test."
        mock_haystack_doc = HaystackDocument(content=mock_doc_content, meta={"source": "README.md", "repo_url": repo_url})
        
        pipeline_output = {
            "llm": {"replies": [mock_answer]},
            "retriever": {"documents": [mock_haystack_doc]}
        }
        mock_query_pipeline_instance.run.return_value = pipeline_output
        
        with patch('agents.pipelines.query_pipeline.QueryPipeline', return_value=mock_query_pipeline_instance):
            service = QueryService(document_store=None) # Initialize with no specific store for this test
            result = service.answer_question(repo_url=repo_url, question=question)

            assert result["query"] == question
            assert result["repo_url"] == repo_url
            assert result["answer"] == mock_answer
            assert len(result["documents"]) == 1
            assert result["documents"][0]["content"] == mock_doc_content
            assert result["documents"][0]["meta"] == {"source": "README.md", "repo_url": repo_url}
            
            expected_pipeline_params = {"query": question, "filters": {"repo_url": repo_url}}
            mock_query_pipeline_instance.run.assert_called_once_with(**expected_pipeline_params)
            assert f"Successfully processed question. Repo: '{repo_url}'" in caplog.text


    @pytest.mark.parametrize("invalid_input, err_message_part, is_repo_url_issue", [
        (("", "A question"), "Question cannot be empty.", False),
        (("   ", "A question"), "Question cannot be empty.", False),
        (("A repo URL", ""), "Question cannot be empty.", False), # Actually, question is empty
        (("A repo URL", "   "), "Question cannot be empty.", False), # Actually, question is empty whitespace
        (("", "A question"), "Repository URL cannot be empty.", True), # Test empty repo_url
    ])
    def test_answer_question_invalid_input(self, mock_query_pipeline_instance, invalid_input, err_message_part, is_repo_url_issue, caplog):
        # Adjust inputs for repo_url vs question
        if is_repo_url_issue:
            repo_url, question = invalid_input[0], invalid_input[1]
        else:
            question, repo_url = invalid_input[0], invalid_input[1]


        with patch('agents.pipelines.query_pipeline.QueryPipeline', return_value=mock_query_pipeline_instance):
            service = QueryService(document_store=None)
            with pytest.raises(HTTPException) as excinfo:
                if is_repo_url_issue:
                     service.answer_question(repo_url="", question="Valid question") # Empty repo_url
                else:
                     service.answer_question(repo_url="valid/url", question=question) # Empty question
            
            assert excinfo.value.status_code == 400
            assert err_message_part in excinfo.value.detail
            if is_repo_url_issue:
                assert "Received an empty or whitespace-only repo_url" in caplog.text
            else:
                assert "Received an empty or whitespace-only question" in caplog.text


    def test_answer_question_pipeline_fails(self, mock_query_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        question = "A valid question"
        mock_query_pipeline_instance.run.side_effect = Exception("Pipeline runtime error")
        
        with patch('agents.pipelines.query_pipeline.QueryPipeline', return_value=mock_query_pipeline_instance):
            service = QueryService(document_store=None)
            with pytest.raises(HTTPException) as excinfo:
                service.answer_question(repo_url=repo_url, question=question)
            
            assert excinfo.value.status_code == 500
            assert "Querying process failed: Pipeline runtime error" in excinfo.value.detail
            assert f"An unexpected error occurred during query processing. Repo: '{repo_url}', Question: '{question}'." in caplog.text

    def test_answer_question_pipeline_returns_none(self, mock_query_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        question = "A valid question"
        mock_query_pipeline_instance.run.return_value = None # Pipeline returns None
        
        with patch('agents.pipelines.query_pipeline.QueryPipeline', return_value=mock_query_pipeline_instance):
            service = QueryService(document_store=None)
            with pytest.raises(HTTPException) as excinfo:
                service.answer_question(repo_url=repo_url, question=question)
            
            assert excinfo.value.status_code == 500
            assert "Query pipeline did not return any output." in excinfo.value.detail
            assert f"QueryPipeline returned empty or None output. Repo: '{repo_url}', Question: '{question}'." in caplog.text


    def test_answer_question_pipeline_output_missing_llm_key(self, mock_query_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        question = "A valid question"
        mock_query_pipeline_instance.run.return_value = {"retriever": {"documents": []}} # Missing 'llm'
        
        with patch('agents.pipelines.query_pipeline.QueryPipeline', return_value=mock_query_pipeline_instance):
            service = QueryService(document_store=None)
            result = service.answer_question(repo_url=repo_url, question=question) # Should not raise exception
            
            assert "Could not find a direct answer" in result["answer"]
            assert not result["documents"] # No documents in this mocked output for retriever either
            assert f"No direct answer found by LLM. Repo: '{repo_url}', Question: '{question}'." in caplog.text


    def test_answer_question_pipeline_output_empty_replies(self, mock_query_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        question = "A valid question"
        mock_query_pipeline_instance.run.return_value = {"llm": {"replies": []}, "retriever": {"documents": []}}
        
        with patch('agents.pipelines.query_pipeline.QueryPipeline', return_value=mock_query_pipeline_instance):
            service = QueryService(document_store=None)
            result = service.answer_question(repo_url=repo_url, question=question)
            
            assert "Could not find a direct answer" in result["answer"]
            assert f"No direct answer found by LLM." in caplog.text


    def test_answer_question_no_documents_retrieved(self, mock_query_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        question = "A valid question"
        mock_answer = "This project is a test."
        
        pipeline_output = {
            "llm": {"replies": [mock_answer]},
            "retriever": {"documents": []} # No documents
        }
        mock_query_pipeline_instance.run.return_value = pipeline_output
        
        with patch('agents.pipelines.query_pipeline.QueryPipeline', return_value=mock_query_pipeline_instance):
            service = QueryService(document_store=None)
            result = service.answer_question(repo_url=repo_url, question=question)
            
            assert result["answer"] == mock_answer
            assert len(result["documents"]) == 0
            assert f"Successfully processed question. Repo: '{repo_url}'" in caplog.text
            
    def test_answer_question_no_answer_and_no_documents(self, mock_query_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        question = "A very obscure question"
        
        pipeline_output = {
            "llm": {"replies": []}, # No answer
            "retriever": {"documents": []} # No documents
        }
        mock_query_pipeline_instance.run.return_value = pipeline_output
        
        with patch('agents.pipelines.query_pipeline.QueryPipeline', return_value=mock_query_pipeline_instance):
            service = QueryService(document_store=None)
            result = service.answer_question(repo_url=repo_url, question=question)
            
            assert result["answer"] == "Sorry, I could not find an answer or any relevant documents for your question."
            assert len(result["documents"]) == 0
            assert f"No direct answer found by LLM. Repo: '{repo_url}', Question: '{question}'." in caplog.text

    def test_answer_question_retriever_output_not_list_of_documents(self, mock_query_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        question = "A valid question"
        mock_answer = "This project is a test."
        
        pipeline_output = {
            "llm": {"replies": [mock_answer]},
            "retriever": {"documents": ["not_a_document_object", HaystackDocument(content="doc2")]}
        }
        mock_query_pipeline_instance.run.return_value = pipeline_output
        
        with patch('agents.pipelines.query_pipeline.QueryPipeline', return_value=mock_query_pipeline_instance):
            service = QueryService(document_store=None)
            result = service.answer_question(repo_url=repo_url, question=question)
            
            assert result["answer"] == mock_answer
            assert len(result["documents"]) == 1 # Only the valid HaystackDocument should be processed
            assert result["documents"][0]["content"] == "doc2"
            assert "Encountered non-Document object in retriever output: <class 'str'>" in caplog.text
