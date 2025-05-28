import pytest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from backend.app.services.query_service import QueryService
from haystack.document_stores import BaseDocumentStore # 用于类型提示
from haystack.schema import Document as HaystackDocument # 用于创建测试文档

# QueryPipeline 类/实例的模拟对象
@pytest.fixture
def mock_query_pipeline_instance():
    mock = MagicMock() 
    mock.run = MagicMock() # run 方法
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
            # 检查 QueryPipeline 是否已使用 document_store 调用
            mock_query_pipeline_class.assert_called_once_with(document_store=mock_document_store)
            assert "QueryService: QueryPipeline 初始化成功。" in caplog.text

    def test_query_service_init_pipeline_fails(self, mock_query_pipeline_class, mock_document_store, caplog):
        mock_query_pipeline_class.side_effect = Exception("Pipeline 初始化错误")
        with patch('agents.pipelines.query_pipeline.QueryPipeline', new=mock_query_pipeline_class):
            with pytest.raises(RuntimeError) as excinfo:
                QueryService(document_store=mock_document_store)
            assert "QueryService: QueryPipeline 初始化失败: Pipeline 初始化错误" in str(excinfo.value)
            assert "QueryService: QueryPipeline 初始化期间发生严重错误。" in caplog.text

    # answer_question 的测试
    def test_answer_question_success(self, mock_query_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        question = "这个项目是关于什么的？"
        
        # 模拟 pipeline 输出
        mock_answer = "这个项目是一个测试。"
        mock_doc_content = "与测试相关的文档内容。"
        mock_haystack_doc = HaystackDocument(content=mock_doc_content, meta={"source": "README.md", "repo_url": repo_url})
        
        pipeline_output = {
            "llm": {"replies": [mock_answer]},
            "retriever": {"documents": [mock_haystack_doc]}
        }
        mock_query_pipeline_instance.run.return_value = pipeline_output
        
        with patch('agents.pipelines.query_pipeline.QueryPipeline', return_value=mock_query_pipeline_instance):
            service = QueryService(document_store=None) # 使用 None 初始化此测试的特定存储
            result = service.answer_question(repo_url=repo_url, question=question)

            assert result["query"] == question
            assert result["repo_url"] == repo_url
            assert result["answer"] == mock_answer
            assert len(result["documents"]) == 1
            assert result["documents"][0]["content"] == mock_doc_content
            assert result["documents"][0]["meta"] == {"source": "README.md", "repo_url": repo_url}
            
            expected_pipeline_params = {"query": question, "filters": {"repo_url": repo_url}}
            mock_query_pipeline_instance.run.assert_called_once_with(**expected_pipeline_params)
            assert f"成功处理问题。仓库: '{repo_url}'" in caplog.text # "Successfully processed question. Repo: '{repo_url}'"


    @pytest.mark.parametrize("invalid_input, err_message_part, is_repo_url_issue", [
        (("", "一个问题"), "问题不能为空。", False), # "Question cannot be empty."
        (("   ", "一个问题"), "问题不能为空。", False), # "Question cannot be empty."
        (("一个仓库 URL", ""), "问题不能为空。", False), # 实际上，问题是空的
        (("一个仓库 URL", "   "), "问题不能为空。", False), # 实际上，问题是空的空格
        (("", "一个问题"), "仓库 URL 不能为空。", True), # "Repository URL cannot be empty." # 测试空 repo_url
    ])
    def test_answer_question_invalid_input(self, mock_query_pipeline_instance, invalid_input, err_message_part, is_repo_url_issue, caplog):
        # 调整 repo_url 与 question 的输入
        if is_repo_url_issue:
            repo_url, question = invalid_input[0], invalid_input[1]
        else:
            question, repo_url = invalid_input[0], invalid_input[1]


        with patch('agents.pipelines.query_pipeline.QueryPipeline', return_value=mock_query_pipeline_instance):
            service = QueryService(document_store=None)
            with pytest.raises(HTTPException) as excinfo:
                if is_repo_url_issue:
                     service.answer_question(repo_url="", question="有效的问题") # 空 repo_url
                else:
                     service.answer_question(repo_url="valid/url", question=question) # 空问题
            
            assert excinfo.value.status_code == 400
            assert err_message_part in excinfo.value.detail
            if is_repo_url_issue:
                assert "收到针对问题" in caplog.text # "Received an empty or whitespace-only repo_url"
            else:
                assert "收到针对 repo_url" in caplog.text # "Received an empty or whitespace-only question"


    def test_answer_question_pipeline_fails(self, mock_query_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        question = "一个有效的问题"
        mock_query_pipeline_instance.run.side_effect = Exception("Pipeline 运行时错误")
        
        with patch('agents.pipelines.query_pipeline.QueryPipeline', return_value=mock_query_pipeline_instance):
            service = QueryService(document_store=None)
            with pytest.raises(HTTPException) as excinfo:
                service.answer_question(repo_url=repo_url, question=question)
            
            assert excinfo.value.status_code == 500
            assert "查询处理期间发生意外错误" in excinfo.value.detail # "Querying process failed: Pipeline runtime error"
            assert f"查询处理期间发生意外错误。仓库: '{repo_url}', 问题: '{question}'。" in caplog.text # "An unexpected error occurred during query processing. Repo: '{repo_url}', Question: '{question}'."

    def test_answer_question_pipeline_returns_none(self, mock_query_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        question = "一个有效的问题"
        mock_query_pipeline_instance.run.return_value = None # Pipeline 返回 None
        
        with patch('agents.pipelines.query_pipeline.QueryPipeline', return_value=mock_query_pipeline_instance):
            service = QueryService(document_store=None)
            with pytest.raises(HTTPException) as excinfo:
                service.answer_question(repo_url=repo_url, question=question)
            
            assert excinfo.value.status_code == 500
            assert "查询 pipeline 未返回任何输出。" in excinfo.value.detail # "Query pipeline did not return any output."
            assert f"QueryPipeline 返回了空或 None 的输出。仓库: '{repo_url}', 问题: '{question}'。" in caplog.text # QueryPipeline returned empty or None output. Repo: '{repo_url}', Question: '{question}'.


    def test_answer_question_pipeline_output_missing_llm_key(self, mock_query_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        question = "一个有效的问题"
        mock_query_pipeline_instance.run.return_value = {"retriever": {"documents": []}} # 缺少 'llm'
        
        with patch('agents.pipelines.query_pipeline.QueryPipeline', return_value=mock_query_pipeline_instance):
            service = QueryService(document_store=None)
            result = service.answer_question(repo_url=repo_url, question=question) # 不应引发异常
            
            assert "未能找到您问题的直接答案" in result["answer"] # "Could not find a direct answer"
            assert not result["documents"] # 在此模拟输出中，retriever 也没有文档
            assert f"LLM 未找到直接答案。仓库: '{repo_url}', 问题: '{question}'。" in caplog.text # "No direct answer found by LLM. Repo: '{repo_url}', Question: '{question}'."


    def test_answer_question_pipeline_output_empty_replies(self, mock_query_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        question = "一个有效的问题"
        mock_query_pipeline_instance.run.return_value = {"llm": {"replies": []}, "retriever": {"documents": []}}
        
        with patch('agents.pipelines.query_pipeline.QueryPipeline', return_value=mock_query_pipeline_instance):
            service = QueryService(document_store=None)
            result = service.answer_question(repo_url=repo_url, question=question)
            
            assert "未能找到您问题的直接答案" in result["answer"] # "Could not find a direct answer"
            assert "LLM 未找到直接答案。" in caplog.text # "No direct answer found by LLM."


    def test_answer_question_no_documents_retrieved(self, mock_query_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        question = "一个有效的问题"
        mock_answer = "这个项目是一个测试。"
        
        pipeline_output = {
            "llm": {"replies": [mock_answer]},
            "retriever": {"documents": []} # 没有文档
        }
        mock_query_pipeline_instance.run.return_value = pipeline_output
        
        with patch('agents.pipelines.query_pipeline.QueryPipeline', return_value=mock_query_pipeline_instance):
            service = QueryService(document_store=None)
            result = service.answer_question(repo_url=repo_url, question=question)
            
            assert result["answer"] == mock_answer
            assert len(result["documents"]) == 0
            assert f"成功处理问题。仓库: '{repo_url}'" in caplog.text # "Successfully processed question. Repo: '{repo_url}'"
            
    def test_answer_question_no_answer_and_no_documents(self, mock_query_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        question = "一个非常模糊的问题"
        
        pipeline_output = {
            "llm": {"replies": []}, # 没有答案
            "retriever": {"documents": []} # 没有文档
        }
        mock_query_pipeline_instance.run.return_value = pipeline_output
        
        with patch('agents.pipelines.query_pipeline.QueryPipeline', return_value=mock_query_pipeline_instance):
            service = QueryService(document_store=None)
            result = service.answer_question(repo_url=repo_url, question=question)
            
            assert result["answer"] == "对不起，根据可用信息，我找不到您问题的答案或任何相关文档。" # "Sorry, I could not find an answer or any relevant documents for your question."
            assert len(result["documents"]) == 0
            assert f"LLM 未找到直接答案。仓库: '{repo_url}', 问题: '{question}'。" in caplog.text # "No direct answer found by LLM. Repo: '{repo_url}', Question: '{question}'."

    def test_answer_question_retriever_output_not_list_of_documents(self, mock_query_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        question = "一个有效的问题"
        mock_answer = "这个项目是一个测试。"
        
        pipeline_output = {
            "llm": {"replies": [mock_answer]},
            "retriever": {"documents": ["not_a_document_object", HaystackDocument(content="doc2")]}
        }
        mock_query_pipeline_instance.run.return_value = pipeline_output
        
        with patch('agents.pipelines.query_pipeline.QueryPipeline', return_value=mock_query_pipeline_instance):
            service = QueryService(document_store=None)
            result = service.answer_question(repo_url=repo_url, question=question)
            
            assert result["answer"] == mock_answer
            assert len(result["documents"]) == 1 # 只应处理有效的 HaystackDocument
            assert result["documents"][0]["content"] == "doc2"
            assert "在 retriever 输出中遇到非 Document 对象: <class 'str'>" in caplog.text # "Encountered non-Document object in retriever output: <class 'str'>"
