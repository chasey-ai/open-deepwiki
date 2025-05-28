import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from fastapi import HTTPException
from backend.app.services.wiki_service import WikiService
from backend.app.services.github_service import GithubService as ActualGithubService # 用于帮助模拟其类型

# GithubService 实例的模拟对象
@pytest.fixture
def mock_github_service_instance():
    mock = MagicMock(spec=ActualGithubService) # 确保它具有 GithubService 的方法
    mock.get_readme_content = AsyncMock() # get_readme_content 是异步的
    return mock

# WikiPipeline 类/实例的模拟对象
@pytest.fixture
def mock_wiki_pipeline_instance():
    mock = MagicMock() # 如果 WikiPipeline 类易于导入，则使用 spec=WikiPipeline
    mock.run = MagicMock() # run 方法
    return mock

@pytest.fixture
def mock_wiki_pipeline_class(mock_wiki_pipeline_instance):
    # 此 fixture 提供一个模拟类，在调用时返回实例。
    mock_class = MagicMock()
    mock_class.return_value = mock_wiki_pipeline_instance
    return mock_class


class TestWikiServiceUnit:

    def test_wiki_service_init_success(self, mock_github_service_instance, mock_wiki_pipeline_class, caplog):
        with patch('agents.pipelines.wiki_pipeline.WikiPipeline', new=mock_wiki_pipeline_class):
            service = WikiService(github_service=mock_github_service_instance)
            assert service.github_service == mock_github_service_instance
            assert service.wiki_pipeline == mock_wiki_pipeline_class.return_value
            mock_wiki_pipeline_class.assert_called_once() # 检查 WikiPipeline 是否已初始化
            assert "WikiService: WikiPipeline 初始化成功。" in caplog.text # "WikiService: WikiPipeline initialized successfully."


    def test_wiki_service_init_pipeline_fails(self, mock_github_service_instance, mock_wiki_pipeline_class, caplog):
        mock_wiki_pipeline_class.side_effect = Exception("Pipeline 初始化错误")
        with patch('agents.pipelines.wiki_pipeline.WikiPipeline', new=mock_wiki_pipeline_class):
            with pytest.raises(RuntimeError) as excinfo:
                WikiService(github_service=mock_github_service_instance)
            assert "WikiService: 关键组件 WikiPipeline 初始化失败: Pipeline 初始化错误" in str(excinfo.value) # "WikiService: Critical component WikiPipeline failed to initialize: Pipeline init error"
            assert "WikiService: WikiPipeline 初始化失败。" in caplog.text # "WikiService: Failed to initialize WikiPipeline."


    @pytest.mark.asyncio
    async def test_generate_wiki_from_repo_readme_success(self, mock_github_service_instance, mock_wiki_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        readme_content = "这是 README 内容。"
        mock_github_service_instance.get_readme_content.return_value = readme_content
        
        generated_text = "生成的 wiki 文本。"
        pipeline_output = {
            "text_generator": { # 基于 WikiService 的解析逻辑
                "results": [generated_text]
            }
        }
        mock_wiki_pipeline_instance.run.return_value = pipeline_output
        
        with patch('agents.pipelines.wiki_pipeline.WikiPipeline', return_value=mock_wiki_pipeline_instance) as MockedPipeline:
            service = WikiService(github_service=mock_github_service_instance)
            result = await service.generate_wiki_from_repo_readme(repo_url)

            assert result == generated_text
            mock_github_service_instance.get_readme_content.assert_awaited_once_with(repo_url)
            expected_pipeline_input = {"repo_url": repo_url, "repo_summary_markdown": readme_content}
            mock_wiki_pipeline_instance.run.assert_called_once_with(data=expected_pipeline_input)
            assert f"成功获取仓库 {repo_url} 的 README。" in caplog.text # "Successfully fetched README for {repo_url}"
            assert f"成功为仓库 {repo_url} 生成 wiki。" in caplog.text # "Successfully generated wiki for {repo_url}"

    @pytest.mark.asyncio
    async def test_generate_wiki_github_service_fails(self, mock_github_service_instance, mock_wiki_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        mock_github_service_instance.get_readme_content.side_effect = HTTPException(
            status_code=404, detail="未找到 README"
        )
        
        with patch('agents.pipelines.wiki_pipeline.WikiPipeline', return_value=mock_wiki_pipeline_instance):
            service = WikiService(github_service=mock_github_service_instance)
            with pytest.raises(HTTPException) as excinfo:
                await service.generate_wiki_from_repo_readme(repo_url)
            
            assert excinfo.value.status_code == 404
            assert excinfo.value.detail == "未找到 README"
            assert f"获取仓库 {repo_url} 的 README 时出错: 未找到 README" in caplog.text # "Error fetching README for {repo_url}: README not found"

    @pytest.mark.asyncio
    async def test_generate_wiki_empty_readme(self, mock_github_service_instance, mock_wiki_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        mock_github_service_instance.get_readme_content.return_value = "   " # 空/仅空格
        
        with patch('agents.pipelines.wiki_pipeline.WikiPipeline', return_value=mock_wiki_pipeline_instance):
            service = WikiService(github_service=mock_github_service_instance)
            with pytest.raises(HTTPException) as excinfo:
                await service.generate_wiki_from_repo_readme(repo_url)
            
            assert excinfo.value.status_code == 404 # 根据当前服务逻辑
            assert f"仓库 {repo_url} 的 README 内容为空或仅包含空格" in excinfo.value.detail # "README content for {repo_url} is empty or consists only of whitespace"
            assert f"仓库 {repo_url} 的 README 内容为空或仅包含空格。" in caplog.text # "README content for {repo_url} is empty or whitespace."

    @pytest.mark.asyncio
    async def test_generate_wiki_pipeline_run_fails(self, mock_github_service_instance, mock_wiki_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        readme_content = "有效的 README。"
        mock_github_service_instance.get_readme_content.return_value = readme_content
        
        mock_wiki_pipeline_instance.run.side_effect = Exception("Pipeline 处理错误")
        
        with patch('agents.pipelines.wiki_pipeline.WikiPipeline', return_value=mock_wiki_pipeline_instance):
            service = WikiService(github_service=mock_github_service_instance)
            with pytest.raises(HTTPException) as excinfo:
                await service.generate_wiki_from_repo_readme(repo_url)
            
            assert excinfo.value.status_code == 500
            assert "Wiki 生成过程失败: Pipeline 处理错误" in excinfo.value.detail # "Wiki generation process failed: Pipeline processing error"
            assert f"WikiPipeline 为仓库 {repo_url} 执行失败: Pipeline 处理错误" in caplog.text # "WikiPipeline execution failed for {repo_url}: Pipeline processing error"

    @pytest.mark.asyncio
    async def test_generate_wiki_pipeline_returns_no_output(self, mock_github_service_instance, mock_wiki_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        readme_content = "有效的 README。"
        mock_github_service_instance.get_readme_content.return_value = readme_content
        mock_wiki_pipeline_instance.run.return_value = None # Pipeline 返回 None
        
        with patch('agents.pipelines.wiki_pipeline.WikiPipeline', return_value=mock_wiki_pipeline_instance):
            service = WikiService(github_service=mock_github_service_instance)
            with pytest.raises(HTTPException) as excinfo:
                await service.generate_wiki_from_repo_readme(repo_url)
            
            assert excinfo.value.status_code == 500
            assert "Wiki 生成 pipeline 未返回任何输出。" in excinfo.value.detail # "Wiki generation pipeline returned no output."
            assert f"WikiPipeline 为仓库 {repo_url} 返回了空或 None 的输出。" in caplog.text # "WikiPipeline returned empty or None output for {repo_url}"

    @pytest.mark.asyncio
    async def test_generate_wiki_pipeline_output_missing_keys(self, mock_github_service_instance, mock_wiki_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        readme_content = "有效的 README。"
        mock_github_service_instance.get_readme_content.return_value = readme_content
        
        # 模拟缺少预期结构的输出
        mock_wiki_pipeline_instance.run.return_value = {"unexpected_key": "some_value"}
        
        with patch('agents.pipelines.wiki_pipeline.WikiPipeline', return_value=mock_wiki_pipeline_instance):
            service = WikiService(github_service=mock_github_service_instance)
            with pytest.raises(HTTPException) as excinfo:
                await service.generate_wiki_from_repo_readme(repo_url)
            
            assert excinfo.value.status_code == 500
            assert "未能从 wiki 生成 pipeline 输出中提取内容。" in excinfo.value.detail # "Failed to extract content from wiki generation pipeline output."
            assert f"无法从 WikiPipeline 为仓库 {repo_url} 的输出中提取生成的 wiki 文本" in caplog.text # "Could not extract generated wiki text from WikiPipeline output for {repo_url}"

    @pytest.mark.asyncio
    async def test_generate_wiki_pipeline_output_empty_results_list(self, mock_github_service_instance, mock_wiki_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        readme_content = "有效的 README。"
        mock_github_service_instance.get_readme_content.return_value = readme_content
        
        pipeline_output_empty_results = {
            "text_generator": {
                "results": [] # 空列表
            }
        }
        mock_wiki_pipeline_instance.run.return_value = pipeline_output_empty_results
        
        with patch('agents.pipelines.wiki_pipeline.WikiPipeline', return_value=mock_wiki_pipeline_instance):
            service = WikiService(github_service=mock_github_service_instance)
            with pytest.raises(HTTPException) as excinfo:
                await service.generate_wiki_from_repo_readme(repo_url)
            
            assert excinfo.value.status_code == 500
            assert "未能从 wiki 生成 pipeline 输出中提取内容。" in excinfo.value.detail # "Failed to extract content from wiki generation pipeline output."

    @pytest.mark.asyncio
    async def test_generate_wiki_unexpected_github_service_error(self, mock_github_service_instance, mock_wiki_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        mock_github_service_instance.get_readme_content.side_effect = Exception("其他一些网络错误")
        
        with patch('agents.pipelines.wiki_pipeline.WikiPipeline', return_value=mock_wiki_pipeline_instance):
            service = WikiService(github_service=mock_github_service_instance)
            with pytest.raises(HTTPException) as excinfo:
                await service.generate_wiki_from_repo_readme(repo_url)
            
            assert excinfo.value.status_code == 500 # 服务将通用错误转换为 500
            assert "获取 README 时发生意外错误: 其他一些网络错误" in excinfo.value.detail # "An unexpected error occurred while fetching README: Some other network error"
            assert f"获取仓库 {repo_url} 的 README 时发生意外错误。" in caplog.text # "Unexpected error fetching README for {repo_url}"

    def test_wiki_service_init_type_error(self):
        with pytest.raises(TypeError) as excinfo:
            WikiService(github_service="not_a_github_service_instance")
        assert "github_service 必须是 GithubService 的实例" in str(excinfo.value) # "github_service must be an instance of GithubService"

    @pytest.mark.asyncio
    async def test_generate_wiki_from_repo_readme_success_with_document_like_object(self, mock_github_service_instance, mock_wiki_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        readme_content = "这是 README 内容。"
        mock_github_service_instance.get_readme_content.return_value = readme_content
        
        # 模拟 pipeline 返回类似 Document 的对象
        class MockDocument:
            def __init__(self, content):
                self.content = content
            def __str__(self): # 用于服务中 str(raw_result) 的回退
                return self.content

        generated_text_obj = MockDocument("通过对象生成的 wiki 文本。")
        pipeline_output = {
            "text_generator": {
                "results": [generated_text_obj]
            }
        }
        mock_wiki_pipeline_instance.run.return_value = pipeline_output
        
        with patch('agents.pipelines.wiki_pipeline.WikiPipeline', return_value=mock_wiki_pipeline_instance):
            service = WikiService(github_service=mock_github_service_instance)
            result = await service.generate_wiki_from_repo_readme(repo_url)

            assert result == "通过对象生成的 wiki 文本。" # 服务应提取 .content
            mock_github_service_instance.get_readme_content.assert_awaited_once_with(repo_url)
            expected_pipeline_input = {"repo_url": repo_url, "repo_summary_markdown": readme_content}
            mock_wiki_pipeline_instance.run.assert_called_once_with(data=expected_pipeline_input)
            assert f"成功为仓库 {repo_url} 生成 wiki。" in caplog.text # "Successfully generated wiki for {repo_url}"

    @pytest.mark.asyncio
    async def test_generate_wiki_from_repo_readme_success_with_plain_string_in_results(self, mock_github_service_instance, mock_wiki_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        readme_content = "这是 README 内容。"
        mock_github_service_instance.get_readme_content.return_value = readme_content
        
        generated_text_str = "  作为纯字符串生成的 wiki 文本。  " # 带空格以测试 strip
        pipeline_output = {
            "text_generator": {
                "results": [generated_text_str]
            }
        }
        mock_wiki_pipeline_instance.run.return_value = pipeline_output
        
        with patch('agents.pipelines.wiki_pipeline.WikiPipeline', return_value=mock_wiki_pipeline_instance):
            service = WikiService(github_service=mock_github_service_instance)
            result = await service.generate_wiki_from_repo_readme(repo_url)

            assert result == "作为纯字符串生成的 wiki 文本。" # 服务应执行 strip()
            mock_github_service_instance.get_readme_content.assert_awaited_once_with(repo_url)
            expected_pipeline_input = {"repo_url": repo_url, "repo_summary_markdown": readme_content}
            mock_wiki_pipeline_instance.run.assert_called_once_with(data=expected_pipeline_input)
            assert f"成功为仓库 {repo_url} 生成 wiki。" in caplog.text # "Successfully generated wiki for {repo_url}"
