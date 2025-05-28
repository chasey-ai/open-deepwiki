import pytest
import httpx
import base64
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from backend.app.services.github_service import GithubService # Adjust import path as necessary

# Test data
VALID_GITHUB_URL = "https://github.com/valid_owner/valid_repo"
VALID_GITHUB_URL_WITH_GIT = "https://github.com/valid_owner/valid_repo.git"
VALID_GITHUB_URL_WITH_PATH = "https://github.com/valid_owner/valid_repo/tree/main"
INVALID_GITHUB_URL_FORMAT = "https://githab.com/invalid/format" # Typo in domain
INVALID_GITHUB_URL_STRUCTURE = "https://github.com/justowner"
INVALID_GITHUB_URL_NON_HTTP = "ftp://github.com/owner/repo"
EMPTY_URL = ""
URL_WITH_INVALID_OWNER_CHARS = "https://github.com/!!!owner/repo"
URL_WITH_INVALID_REPO_CHARS = "https://github.com/owner/repo$$$"


@pytest.fixture
def github_service():
    """Provides an instance of GithubService for testing."""
    # Mock os.getenv for GITHUB_API_TOKEN if you want to test token presence
    with patch('os.getenv') as mock_getenv:
        mock_getenv.return_value = "fake_test_token" # Simulate token is set
        service = GithubService()
        # Ensure headers are updated if token is present
        if service.github_api_token:
            assert service.headers["Authorization"] == f"token {service.github_api_token}"
        return service

class TestGithubServiceUnit:

    # Tests for _extract_owner_repo_from_url
    @pytest.mark.parametrize("url, expected_owner, expected_repo", [
        (VALID_GITHUB_URL, "valid_owner", "valid_repo"),
        (VALID_GITHUB_URL_WITH_GIT, "valid_owner", "valid_repo"),
        (VALID_GITHUB_URL_WITH_PATH, "valid_owner", "valid_repo"),
        ("https://github.com/owner-with-hyphens/repo-with-hyphens.git", "owner-with-hyphens", "repo-with-hyphens"),
        ("https://github.com/owner_with_underscores/repo.with.dots_underscores", "owner_with_underscores", "repo.with.dots_underscores"),
    ])
    def test_extract_owner_repo_from_url_valid(self, github_service: GithubService, url, expected_owner, expected_repo):
        owner, repo = github_service._extract_owner_repo_from_url(url)
        assert owner == expected_owner
        assert repo == expected_repo

    @pytest.mark.parametrize("invalid_url, expected_exception_message_part", [
        (INVALID_GITHUB_URL_FORMAT, "Invalid GitHub repository URL format"),
        (INVALID_GITHUB_URL_STRUCTURE, "Invalid GitHub repository URL format"),
        (INVALID_GITHUB_URL_NON_HTTP, "Invalid GitHub repository URL format"),
        (EMPTY_URL, "Repository URL must be a string"), # or format depending on how it's caught
        ("https://github.com//repo", "Invalid owner name format"), # Empty owner
        ("https://github.com/owner/", "Invalid repository name format"), # Empty repo (assuming regex catches this)
        (URL_WITH_INVALID_OWNER_CHARS, "Invalid owner name format"),
        (URL_WITH_INVALID_REPO_CHARS, "Invalid repository name format"),
        (None, "Repository URL must be a string"),
        ("http://github.com/owner/repo", "Invalid GitHub repository URL format") # Non-HTTPS
    ])
    def test_extract_owner_repo_from_url_invalid(self, github_service: GithubService, invalid_url, expected_exception_message_part):
        with pytest.raises(ValueError) as excinfo:
            github_service._extract_owner_repo_from_url(invalid_url)
        assert expected_exception_message_part in str(excinfo.value)

    # Tests for get_readme_content
    @pytest.mark.asyncio
    async def test_get_readme_content_success(self, github_service: GithubService):
        mock_readme_text = "This is the README content."
        mock_readme_base64 = base64.b64encode(mock_readme_text.encode('utf-8')).decode('utf-8')
        
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": mock_readme_base64, "encoding": "base64"}
        
        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.get.return_value = mock_response
        
        with patch('httpx.AsyncClient', return_value=mock_async_client) as mock_client_constructor:
            readme_content = await github_service.get_readme_content(VALID_GITHUB_URL)
            
            mock_client_constructor.assert_called_once_with(timeout=10.0)
            expected_api_url = "https://api.github.com/repos/valid_owner/valid_repo/readme"
            mock_async_client.get.assert_called_once_with(expected_api_url, headers=github_service.headers)
            assert readme_content == mock_readme_text

    @pytest.mark.asyncio
    async def test_get_readme_content_repo_not_found_or_readme_missing(self, github_service: GithubService):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.request = MagicMock(spec=httpx.Request) # Add request attribute
        mock_response.request.url = "https://api.github.com/repos/owner/repo/readme"


        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        # Configure .get to raise HTTPStatusError for 404
        mock_async_client.get.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=mock_response.request, response=mock_response
        )
        
        with patch('httpx.AsyncClient', return_value=mock_async_client):
            with pytest.raises(HTTPException) as excinfo:
                await github_service.get_readme_content(VALID_GITHUB_URL)
            assert excinfo.value.status_code == 404
            assert "README not found" in excinfo.value.detail or "repository itself not found" in excinfo.value.detail


    @pytest.mark.asyncio
    async def test_get_readme_content_forbidden(self, github_service: GithubService):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_response.request = MagicMock(spec=httpx.Request)
        mock_response.request.url = "https://api.github.com/repos/owner/repo/readme"

        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.get.side_effect = httpx.HTTPStatusError(
            "403 Forbidden", request=mock_response.request, response=mock_response
        )

        with patch('httpx.AsyncClient', return_value=mock_async_client):
            with pytest.raises(HTTPException) as excinfo:
                await github_service.get_readme_content(VALID_GITHUB_URL)
            assert excinfo.value.status_code == 403
            assert "Access to GitHub API forbidden" in excinfo.value.detail
            
    @pytest.mark.asyncio
    async def test_get_readme_content_github_api_other_error(self, github_service: GithubService):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500 # Internal Server Error
        mock_response.text = "Internal Server Error"
        mock_response.request = MagicMock(spec=httpx.Request)
        mock_response.request.url = "https://api.github.com/repos/owner/repo/readme"

        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.get.side_effect = httpx.HTTPStatusError(
            "500 Internal Server Error", request=mock_response.request, response=mock_response
        )
        
        with patch('httpx.AsyncClient', return_value=mock_async_client):
            with pytest.raises(HTTPException) as excinfo:
                await github_service.get_readme_content(VALID_GITHUB_URL)
            assert excinfo.value.status_code == 500
            assert "GitHub API error (500)" in excinfo.value.detail

    @pytest.mark.asyncio
    async def test_get_readme_content_network_error(self, github_service: GithubService):
        mock_request = MagicMock(spec=httpx.Request) # Create a mock request object
        mock_request.url = "https://api.github.com/repos/owner/repo/readme"

        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.get.side_effect = httpx.RequestError("Network error", request=mock_request)
        
        with patch('httpx.AsyncClient', return_value=mock_async_client):
            with pytest.raises(HTTPException) as excinfo:
                await github_service.get_readme_content(VALID_GITHUB_URL)
            assert excinfo.value.status_code == 503 # Service Unavailable
            assert "Error connecting to GitHub API" in excinfo.value.detail

    @pytest.mark.asyncio
    async def test_get_readme_content_timeout_error(self, github_service: GithubService):
        mock_request = MagicMock(spec=httpx.Request)
        mock_request.url = "https://api.github.com/repos/owner/repo/readme"
        
        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.get.side_effect = httpx.TimeoutException("Timeout", request=mock_request)

        with patch('httpx.AsyncClient', return_value=mock_async_client):
            with pytest.raises(HTTPException) as excinfo:
                await github_service.get_readme_content(VALID_GITHUB_URL)
            assert excinfo.value.status_code == 408 # Request Timeout
            assert "Request to GitHub API timed out" in excinfo.value.detail


    @pytest.mark.asyncio
    async def test_get_readme_content_invalid_base64(self, github_service: GithubService):
        invalid_base64_content = "This is not valid base64 content %$#"
        
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": invalid_base64_content, "encoding": "base64"}
        
        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.get.return_value = mock_response
        
        with patch('httpx.AsyncClient', return_value=mock_async_client):
            with pytest.raises(HTTPException) as excinfo:
                await github_service.get_readme_content(VALID_GITHUB_URL)
            assert excinfo.value.status_code == 500
            assert "Error decoding README content from Base64" in excinfo.value.detail

    @pytest.mark.asyncio
    async def test_get_readme_content_no_content_key_in_response(self, github_service: GithubService):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"encoding": "base64"} # Missing "content" key
        
        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.get.return_value = mock_response
        
        with patch('httpx.AsyncClient', return_value=mock_async_client):
            with pytest.raises(HTTPException) as excinfo:
                await github_service.get_readme_content(VALID_GITHUB_URL)
            assert excinfo.value.status_code == 404 # As per current service code
            assert "README content not found or is empty in API response" in excinfo.value.detail
            
    @pytest.mark.asyncio
    async def test_get_readme_content_empty_content_value_in_response(self, github_service: GithubService):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": "", "encoding": "base64"} # Empty "content"
        
        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.get.return_value = mock_response
        
        with patch('httpx.AsyncClient', return_value=mock_async_client):
            with pytest.raises(HTTPException) as excinfo:
                await github_service.get_readme_content(VALID_GITHUB_URL)
            assert excinfo.value.status_code == 404
            assert "README content not found or is empty in API response" in excinfo.value.detail

    def test_github_service_init_no_token(self):
        # Test GithubService initialization when GITHUB_API_TOKEN is not set
        with patch('os.getenv') as mock_getenv:
            mock_getenv.return_value = None # Simulate token is NOT set
            service = GithubService()
            assert service.github_api_token is None
            assert "Authorization" not in service.headers # Authorization header should not be set

    def test_github_service_init_with_token(self):
        # Test GithubService initialization when GITHUB_API_TOKEN IS set
        fake_token = "my_super_secret_github_token"
        with patch('os.getenv') as mock_getenv:
            mock_getenv.return_value = fake_token
            service = GithubService()
            assert service.github_api_token == fake_token
            assert "Authorization" in service.headers
            assert service.headers["Authorization"] == f"token {fake_token}"

    @pytest.mark.asyncio
    async def test_get_readme_content_unauthorized_401(self, github_service: GithubService):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401 
        mock_response.text = "Unauthorized"
        mock_response.request = MagicMock(spec=httpx.Request)
        mock_response.request.url = "https://api.github.com/repos/owner/repo/readme"

        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.get.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized", request=mock_response.request, response=mock_response
        )
        
        with patch('httpx.AsyncClient', return_value=mock_async_client):
            with pytest.raises(HTTPException) as excinfo:
                await github_service.get_readme_content(VALID_GITHUB_URL)
            assert excinfo.value.status_code == 401
            assert "Unauthorized access to GitHub API" in excinfo.value.detail

    @pytest.mark.asyncio
    async def test_get_readme_content_forbidden_no_token_message_variant(self):
        # Test the specific 403 message when no token is configured
        with patch('os.getenv') as mock_getenv:
            mock_getenv.return_value = None # No token
            service_no_token = GithubService() # Instance without token

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_response.request = MagicMock(spec=httpx.Request)
        mock_response.request.url = "https://api.github.com/repos/owner/repo/readme"

        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.get.side_effect = httpx.HTTPStatusError(
            "403 Forbidden", request=mock_response.request, response=mock_response
        )

        with patch('httpx.AsyncClient', return_value=mock_async_client):
            with pytest.raises(HTTPException) as excinfo:
                await service_no_token.get_readme_content(VALID_GITHUB_URL)
            assert excinfo.value.status_code == 403
            assert "GITHUB_API_TOKEN is not set or provided" in excinfo.value.detail
            
    @pytest.mark.asyncio
    async def test_get_readme_content_forbidden_with_token_message_variant(self, github_service: GithubService):
        # This test uses the fixture `github_service` which has a token
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_response.request = MagicMock(spec=httpx.Request)
        mock_response.request.url = "https://api.github.com/repos/owner/repo/readme"

        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.get.side_effect = httpx.HTTPStatusError(
            "403 Forbidden", request=mock_response.request, response=mock_response
        )

        with patch('httpx.AsyncClient', return_value=mock_async_client):
            with pytest.raises(HTTPException) as excinfo:
                await github_service.get_readme_content(VALID_GITHUB_URL) # github_service has a token
            assert excinfo.value.status_code == 403
            assert "Check your GITHUB_API_TOKEN's permissions" in excinfo.value.detail
            
    # Test _extract_owner_repo_from_url with more complex valid URLs
    @pytest.mark.parametrize("url, expected_owner, expected_repo", [
        ("https://github.com/user-name/repo-name.git", "user-name", "repo-name"),
        ("https://github.com/user.name/repo.name", "user.name", "repo.name"), # Owner names can't have periods per GitHub, but regex was more permissive. Let's test against the stricter regex.
        ("https://github.com/UserName/RepoName", "UserName", "RepoName"),
        ("https://github.com/a/b", "a", "b"), # Short names
        ("https://github.com/owner/repo-name-with-numbers123", "owner", "repo-name-with-numbers123"),
        ("https://github.com/owner/repo.git.git", "owner", "repo.git"), # .git at end is stripped, one .git remains.
    ])
    def test_extract_owner_repo_from_url_more_valid_cases(self, github_service: GithubService, url, expected_owner, expected_repo):
        # Current regex for owner: ^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$
        # Current regex for repo: ^[a-zA-Z0-9_.-]{1,100}$
        # The case "user.name" for an owner will fail the owner regex. This is correct.
        if "." in expected_owner:
             with pytest.raises(ValueError) as excinfo:
                github_service._extract_owner_repo_from_url(url)
             assert "Invalid owner name format" in str(excinfo.value)
        else:
            owner, repo = github_service._extract_owner_repo_from_url(url)
            assert owner == expected_owner
            assert repo == expected_repo

    @pytest.mark.parametrize("invalid_url_for_regex_specifics", [
        ("https://github.com/-owner/repo"), # Owner starts with hyphen
        ("https://github.com/owner-/repo"), # Owner ends with hyphen
        ("https://github.com/owner/repo..name"), # Repo contains ..
        ("https://github.com/owner/.repo"), # Repo starts with . (valid by GitHub, but current regex for repo does not allow start with - or .)
        ("https://github.com/owner/-repo"), # Repo starts with -
    ])
    def test_extract_owner_repo_from_url_regex_edge_cases(self, github_service: GithubService, invalid_url_for_regex_specifics):
        with pytest.raises(ValueError) as excinfo:
            github_service._extract_owner_repo_from_url(invalid_url_for_regex_specifics)
        # Check that it's a ValueError, specific message depends on which part failed
        assert "Invalid owner name format" in str(excinfo.value) or "Invalid repository name format" in str(excinfo.value)

    @pytest.mark.parametrize("url_with_subpath", [
        ("https://github.com/owner/repo/issues"),
        ("https://github.com/owner/repo/pulls/1"),
        ("https://github.com/owner/repo/blob/main/README.md"),
    ])
    def test_extract_owner_repo_from_url_handles_subpaths(self, github_service: GithubService, url_with_subpath):
        # The regex `^https://github\.com/([a-zA-Z0-9.-]+)/([a-zA-Z0-9_.-]+)`
        # should correctly capture just "owner" and "repo" and ignore subpaths.
        owner, repo = github_service._extract_owner_repo_from_url(url_with_subpath)
        assert owner == "owner"
        assert repo == "repo"

    @pytest.mark.asyncio
    async def test_get_readme_content_invalid_url_passed_to_readme_fetch(self, github_service: GithubService):
        # Test that if _extract_owner_repo_from_url fails, get_readme_content raises HTTPException
        invalid_url = "htp://badurl.com"
        with pytest.raises(HTTPException) as excinfo:
            await github_service.get_readme_content(invalid_url)
        assert excinfo.value.status_code == 400
        assert "Invalid GitHub repository URL" in excinfo.value.detail
