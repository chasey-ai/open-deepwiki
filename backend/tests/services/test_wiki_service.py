import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from fastapi import HTTPException
from backend.app.services.wiki_service import WikiService
from backend.app.services.github_service import GithubService as ActualGithubService # To help mock its type

# Mock for GithubService instance
@pytest.fixture
def mock_github_service_instance():
    mock = MagicMock(spec=ActualGithubService) # Ensures it has methods of GithubService
    mock.get_readme_content = AsyncMock() # get_readme_content is async
    return mock

# Mock for WikiPipeline class/instance
@pytest.fixture
def mock_wiki_pipeline_instance():
    mock = MagicMock() # spec=WikiPipeline if WikiPipeline class is easily importable
    mock.run = MagicMock() # run method
    return mock

@pytest.fixture
def mock_wiki_pipeline_class(mock_wiki_pipeline_instance):
    # This fixture provides a mock class that returns the instance when called.
    mock_class = MagicMock()
    mock_class.return_value = mock_wiki_pipeline_instance
    return mock_class


class TestWikiServiceUnit:

    def test_wiki_service_init_success(self, mock_github_service_instance, mock_wiki_pipeline_class, caplog):
        with patch('agents.pipelines.wiki_pipeline.WikiPipeline', new=mock_wiki_pipeline_class):
            service = WikiService(github_service=mock_github_service_instance)
            assert service.github_service == mock_github_service_instance
            assert service.wiki_pipeline == mock_wiki_pipeline_class.return_value
            mock_wiki_pipeline_class.assert_called_once() # Check WikiPipeline was initialized
            assert "WikiService: WikiPipeline initialized successfully." in caplog.text


    def test_wiki_service_init_pipeline_fails(self, mock_github_service_instance, mock_wiki_pipeline_class, caplog):
        mock_wiki_pipeline_class.side_effect = Exception("Pipeline init error")
        with patch('agents.pipelines.wiki_pipeline.WikiPipeline', new=mock_wiki_pipeline_class):
            with pytest.raises(RuntimeError) as excinfo:
                WikiService(github_service=mock_github_service_instance)
            assert "WikiService: Critical component WikiPipeline failed to initialize: Pipeline init error" in str(excinfo.value)
            assert "WikiService: Failed to initialize WikiPipeline." in caplog.text


    @pytest.mark.asyncio
    async def test_generate_wiki_from_repo_readme_success(self, mock_github_service_instance, mock_wiki_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        readme_content = "This is the README."
        mock_github_service_instance.get_readme_content.return_value = readme_content
        
        generated_text = "Generated wiki text here."
        pipeline_output = {
            "text_generator": { # Based on WikiService's parsing logic
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
            assert f"Successfully fetched README for {repo_url}" in caplog.text
            assert f"Successfully generated wiki for {repo_url}" in caplog.text

    @pytest.mark.asyncio
    async def test_generate_wiki_github_service_fails(self, mock_github_service_instance, mock_wiki_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        mock_github_service_instance.get_readme_content.side_effect = HTTPException(
            status_code=404, detail="README not found"
        )
        
        with patch('agents.pipelines.wiki_pipeline.WikiPipeline', return_value=mock_wiki_pipeline_instance):
            service = WikiService(github_service=mock_github_service_instance)
            with pytest.raises(HTTPException) as excinfo:
                await service.generate_wiki_from_repo_readme(repo_url)
            
            assert excinfo.value.status_code == 404
            assert excinfo.value.detail == "README not found"
            assert f"Error fetching README for {repo_url}: README not found" in caplog.text

    @pytest.mark.asyncio
    async def test_generate_wiki_empty_readme(self, mock_github_service_instance, mock_wiki_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        mock_github_service_instance.get_readme_content.return_value = "   " # Empty/whitespace
        
        with patch('agents.pipelines.wiki_pipeline.WikiPipeline', return_value=mock_wiki_pipeline_instance):
            service = WikiService(github_service=mock_github_service_instance)
            with pytest.raises(HTTPException) as excinfo:
                await service.generate_wiki_from_repo_readme(repo_url)
            
            assert excinfo.value.status_code == 404 # As per current service logic
            assert f"README content for {repo_url} is empty or consists only of whitespace" in excinfo.value.detail
            assert f"README content for {repo_url} is empty or whitespace." in caplog.text

    @pytest.mark.asyncio
    async def test_generate_wiki_pipeline_run_fails(self, mock_github_service_instance, mock_wiki_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        readme_content = "Valid README."
        mock_github_service_instance.get_readme_content.return_value = readme_content
        
        mock_wiki_pipeline_instance.run.side_effect = Exception("Pipeline processing error")
        
        with patch('agents.pipelines.wiki_pipeline.WikiPipeline', return_value=mock_wiki_pipeline_instance):
            service = WikiService(github_service=mock_github_service_instance)
            with pytest.raises(HTTPException) as excinfo:
                await service.generate_wiki_from_repo_readme(repo_url)
            
            assert excinfo.value.status_code == 500
            assert "Wiki generation process failed: Pipeline processing error" in excinfo.value.detail
            assert f"WikiPipeline execution failed for {repo_url}: Pipeline processing error" in caplog.text

    @pytest.mark.asyncio
    async def test_generate_wiki_pipeline_returns_no_output(self, mock_github_service_instance, mock_wiki_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        readme_content = "Valid README."
        mock_github_service_instance.get_readme_content.return_value = readme_content
        mock_wiki_pipeline_instance.run.return_value = None # Pipeline returns None
        
        with patch('agents.pipelines.wiki_pipeline.WikiPipeline', return_value=mock_wiki_pipeline_instance):
            service = WikiService(github_service=mock_github_service_instance)
            with pytest.raises(HTTPException) as excinfo:
                await service.generate_wiki_from_repo_readme(repo_url)
            
            assert excinfo.value.status_code == 500
            assert "Wiki generation pipeline returned no output." in excinfo.value.detail
            assert f"WikiPipeline returned empty or None output for {repo_url}" in caplog.text

    @pytest.mark.asyncio
    async def test_generate_wiki_pipeline_output_missing_keys(self, mock_github_service_instance, mock_wiki_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        readme_content = "Valid README."
        mock_github_service_instance.get_readme_content.return_value = readme_content
        
        # Simulate output that's missing the expected structure
        mock_wiki_pipeline_instance.run.return_value = {"unexpected_key": "some_value"}
        
        with patch('agents.pipelines.wiki_pipeline.WikiPipeline', return_value=mock_wiki_pipeline_instance):
            service = WikiService(github_service=mock_github_service_instance)
            with pytest.raises(HTTPException) as excinfo:
                await service.generate_wiki_from_repo_readme(repo_url)
            
            assert excinfo.value.status_code == 500
            assert "Failed to extract content from wiki generation pipeline output." in excinfo.value.detail
            assert f"Could not extract generated wiki text from WikiPipeline output for {repo_url}" in caplog.text

    @pytest.mark.asyncio
    async def test_generate_wiki_pipeline_output_empty_results_list(self, mock_github_service_instance, mock_wiki_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        readme_content = "Valid README."
        mock_github_service_instance.get_readme_content.return_value = readme_content
        
        pipeline_output_empty_results = {
            "text_generator": {
                "results": [] # Empty list
            }
        }
        mock_wiki_pipeline_instance.run.return_value = pipeline_output_empty_results
        
        with patch('agents.pipelines.wiki_pipeline.WikiPipeline', return_value=mock_wiki_pipeline_instance):
            service = WikiService(github_service=mock_github_service_instance)
            with pytest.raises(HTTPException) as excinfo:
                await service.generate_wiki_from_repo_readme(repo_url)
            
            assert excinfo.value.status_code == 500
            assert "Failed to extract content from wiki generation pipeline output." in excinfo.value.detail

    @pytest.mark.asyncio
    async def test_generate_wiki_unexpected_github_service_error(self, mock_github_service_instance, mock_wiki_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        mock_github_service_instance.get_readme_content.side_effect = Exception("Some other network error")
        
        with patch('agents.pipelines.wiki_pipeline.WikiPipeline', return_value=mock_wiki_pipeline_instance):
            service = WikiService(github_service=mock_github_service_instance)
            with pytest.raises(HTTPException) as excinfo:
                await service.generate_wiki_from_repo_readme(repo_url)
            
            assert excinfo.value.status_code == 500 # Service converts generic error to 500
            assert "An unexpected error occurred while fetching README: Some other network error" in excinfo.value.detail
            assert f"Unexpected error fetching README for {repo_url}" in caplog.text

    def test_wiki_service_init_type_error(self):
        with pytest.raises(TypeError) as excinfo:
            WikiService(github_service="not_a_github_service_instance")
        assert "github_service must be an instance of GithubService" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_generate_wiki_from_repo_readme_success_with_document_like_object(self, mock_github_service_instance, mock_wiki_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        readme_content = "This is the README."
        mock_github_service_instance.get_readme_content.return_value = readme_content
        
        # Simulate pipeline returning a Document-like object
        class MockDocument:
            def __init__(self, content):
                self.content = content
            def __str__(self): # For the str(raw_result) fallback in service
                return self.content

        generated_text_obj = MockDocument("Generated wiki text via object.")
        pipeline_output = {
            "text_generator": {
                "results": [generated_text_obj]
            }
        }
        mock_wiki_pipeline_instance.run.return_value = pipeline_output
        
        with patch('agents.pipelines.wiki_pipeline.WikiPipeline', return_value=mock_wiki_pipeline_instance):
            service = WikiService(github_service=mock_github_service_instance)
            result = await service.generate_wiki_from_repo_readme(repo_url)

            assert result == "Generated wiki text via object." # Service should extract .content
            mock_github_service_instance.get_readme_content.assert_awaited_once_with(repo_url)
            expected_pipeline_input = {"repo_url": repo_url, "repo_summary_markdown": readme_content}
            mock_wiki_pipeline_instance.run.assert_called_once_with(data=expected_pipeline_input)
            assert f"Successfully generated wiki for {repo_url}" in caplog.text

    @pytest.mark.asyncio
    async def test_generate_wiki_from_repo_readme_success_with_plain_string_in_results(self, mock_github_service_instance, mock_wiki_pipeline_instance, caplog):
        repo_url = "https://github.com/test/repo"
        readme_content = "This is the README."
        mock_github_service_instance.get_readme_content.return_value = readme_content
        
        generated_text_str = "  Generated wiki text as plain string.  " # With spaces to test strip
        pipeline_output = {
            "text_generator": {
                "results": [generated_text_str]
            }
        }
        mock_wiki_pipeline_instance.run.return_value = pipeline_output
        
        with patch('agents.pipelines.wiki_pipeline.WikiPipeline', return_value=mock_wiki_pipeline_instance):
            service = WikiService(github_service=mock_github_service_instance)
            result = await service.generate_wiki_from_repo_readme(repo_url)

            assert result == "Generated wiki text as plain string." # Service should strip()
            mock_github_service_instance.get_readme_content.assert_awaited_once_with(repo_url)
            expected_pipeline_input = {"repo_url": repo_url, "repo_summary_markdown": readme_content}
            mock_wiki_pipeline_instance.run.assert_called_once_with(data=expected_pipeline_input)
            assert f"Successfully generated wiki for {repo_url}" in caplog.text
