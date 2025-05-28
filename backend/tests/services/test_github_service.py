import pytest
import httpx
import base64
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from backend.app.services.github_service import GithubService # 根据需要调整导入路径

# 测试数据
VALID_GITHUB_URL = "https://github.com/valid_owner/valid_repo"
VALID_GITHUB_URL_WITH_GIT = "https://github.com/valid_owner/valid_repo.git"
VALID_GITHUB_URL_WITH_PATH = "https://github.com/valid_owner/valid_repo/tree/main"
INVALID_GITHUB_URL_FORMAT = "https://githab.com/invalid/format" # 域名拼写错误
INVALID_GITHUB_URL_STRUCTURE = "https://github.com/justowner"
INVALID_GITHUB_URL_NON_HTTP = "ftp://github.com/owner/repo"
EMPTY_URL = ""
URL_WITH_INVALID_OWNER_CHARS = "https://github.com/!!!owner/repo"
URL_WITH_INVALID_REPO_CHARS = "https://github.com/owner/repo$$$"


@pytest.fixture
def github_service():
    """提供一个用于测试的 GithubService 实例。"""
    # 如果要测试 GITHUB_API_TOKEN 是否存在，可以模拟 os.getenv
    with patch('os.getenv') as mock_getenv:
        mock_getenv.return_value = "fake_test_token" # 模拟已设置令牌
        service = GithubService()
        # 确保如果令牌存在，请求头已更新
        if service.github_api_token:
            assert service.headers["Authorization"] == f"token {service.github_api_token}"
        return service

class TestGithubServiceUnit:

    # _extract_owner_repo_from_url 的测试
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
        (INVALID_GITHUB_URL_FORMAT, "无效的 GitHub 仓库 URL 格式"), 
        (INVALID_GITHUB_URL_STRUCTURE, "无效的 GitHub 仓库 URL 格式"), 
        (INVALID_GITHUB_URL_NON_HTTP, "无效的 GitHub 仓库 URL 格式"), 
        (EMPTY_URL, "仓库 URL 必须是字符串。"), # 或根据捕获方式判断格式
        ("https://github.com//repo", "无效的所有者名称格式"), # 空所有者
        ("https://github.com/owner/", "无效的仓库名称格式"), # 空仓库 (假设正则表达式捕获此情况)
        (URL_WITH_INVALID_OWNER_CHARS, "无效的所有者名称格式"), 
        (URL_WITH_INVALID_REPO_CHARS, "无效的仓库名称格式"), 
        (None, "仓库 URL 必须是字符串。"), 
        ("http://github.com/owner/repo", "无效的 GitHub 仓库 URL 格式") # 非 HTTPS
    ])
    def test_extract_owner_repo_from_url_invalid(self, github_service: GithubService, invalid_url, expected_exception_message_part):
        with pytest.raises(ValueError) as excinfo:
            github_service._extract_owner_repo_from_url(invalid_url)
        assert expected_exception_message_part in str(excinfo.value)

    # get_readme_content 的测试
    @pytest.mark.asyncio
    async def test_get_readme_content_success(self, github_service: GithubService):
        mock_readme_text = "这是 README 内容。"
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
        mock_response.text = "未找到"
        mock_response.request = MagicMock(spec=httpx.Request) # 添加 request 属性
        mock_response.request.url = "https://api.github.com/repos/owner/repo/readme"


        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        # 配置 .get 以针对 404 引发 HTTPStatusError
        mock_async_client.get.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=mock_response.request, response=mock_response
        )
        
        with patch('httpx.AsyncClient', return_value=mock_async_client):
            with pytest.raises(HTTPException) as excinfo:
                await github_service.get_readme_content(VALID_GITHUB_URL)
            assert excinfo.value.status_code == 404
            assert "未找到 README" in excinfo.value.detail or "仓库本身未找到" in excinfo.value.detail


    @pytest.mark.asyncio
    async def test_get_readme_content_forbidden(self, github_service: GithubService):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403
        mock_response.text = "禁止访问"
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
            assert "禁止访问 GitHub API" in excinfo.value.detail
            
    @pytest.mark.asyncio
    async def test_get_readme_content_github_api_other_error(self, github_service: GithubService):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500 # 内部服务器错误
        mock_response.text = "内部服务器错误"
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
            assert "GitHub API 错误 (500)" in excinfo.value.detail

    @pytest.mark.asyncio
    async def test_get_readme_content_network_error(self, github_service: GithubService):
        mock_request = MagicMock(spec=httpx.Request) # 创建一个模拟请求对象
        mock_request.url = "https://api.github.com/repos/owner/repo/readme"

        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.get.side_effect = httpx.RequestError("网络错误", request=mock_request)
        
        with patch('httpx.AsyncClient', return_value=mock_async_client):
            with pytest.raises(HTTPException) as excinfo:
                await github_service.get_readme_content(VALID_GITHUB_URL)
            assert excinfo.value.status_code == 503 # 服务不可用
            assert "连接 GitHub API 时出错" in excinfo.value.detail

    @pytest.mark.asyncio
    async def test_get_readme_content_timeout_error(self, github_service: GithubService):
        mock_request = MagicMock(spec=httpx.Request)
        mock_request.url = "https://api.github.com/repos/owner/repo/readme"
        
        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.get.side_effect = httpx.TimeoutException("超时", request=mock_request)

        with patch('httpx.AsyncClient', return_value=mock_async_client):
            with pytest.raises(HTTPException) as excinfo:
                await github_service.get_readme_content(VALID_GITHUB_URL)
            assert excinfo.value.status_code == 408 # 请求超时
            assert "请求 GitHub API 超时" in excinfo.value.detail


    @pytest.mark.asyncio
    async def test_get_readme_content_invalid_base64(self, github_service: GithubService):
        invalid_base64_content = "这不是有效的 base64 内容 %$#"
        
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": invalid_base64_content, "encoding": "base64"}
        
        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.get.return_value = mock_response
        
        with patch('httpx.AsyncClient', return_value=mock_async_client):
            with pytest.raises(HTTPException) as excinfo:
                await github_service.get_readme_content(VALID_GITHUB_URL)
            assert excinfo.value.status_code == 500
            assert "从 Base64 解码 README 内容时出错" in excinfo.value.detail

    @pytest.mark.asyncio
    async def test_get_readme_content_no_content_key_in_response(self, github_service: GithubService):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"encoding": "base64"} # 缺少 "content" 键
        
        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.get.return_value = mock_response
        
        with patch('httpx.AsyncClient', return_value=mock_async_client):
            with pytest.raises(HTTPException) as excinfo:
                await github_service.get_readme_content(VALID_GITHUB_URL)
            assert excinfo.value.status_code == 404 # 根据当前服务代码
            assert "API 响应中未找到 README 内容或是空的" in excinfo.value.detail
            
    @pytest.mark.asyncio
    async def test_get_readme_content_empty_content_value_in_response(self, github_service: GithubService):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": "", "encoding": "base64"} # 空 "content"
        
        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.get.return_value = mock_response
        
        with patch('httpx.AsyncClient', return_value=mock_async_client):
            with pytest.raises(HTTPException) as excinfo:
                await github_service.get_readme_content(VALID_GITHUB_URL)
            assert excinfo.value.status_code == 404
            assert "API 响应中未找到 README 内容或是空的" in excinfo.value.detail

    def test_github_service_init_no_token(self):
        # 测试未设置 GITHUB_API_TOKEN 时 GithubService 的初始化
        with patch('os.getenv') as mock_getenv:
            mock_getenv.return_value = None # 模拟未设置令牌
            service = GithubService()
            assert service.github_api_token is None
            assert "Authorization" not in service.headers # 不应设置 Authorization 请求头

    def test_github_service_init_with_token(self):
        # 测试设置了 GITHUB_API_TOKEN 时 GithubService 的初始化
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
        mock_response.text = "未授权"
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
            assert "未授权访问 GitHub API" in excinfo.value.detail

    @pytest.mark.asyncio
    async def test_get_readme_content_forbidden_no_token_message_variant(self):
        # 测试未配置令牌时特定的 403 消息
        with patch('os.getenv') as mock_getenv:
            mock_getenv.return_value = None # 无令牌
            service_no_token = GithubService() # 无令牌的实例

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403
        mock_response.text = "禁止访问"
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
            assert "GITHUB_API_TOKEN 未设置或未提供" in excinfo.value.detail
            
    @pytest.mark.asyncio
    async def test_get_readme_content_forbidden_with_token_message_variant(self, github_service: GithubService):
        # 此测试使用具有令牌的 `github_service` fixture
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403
        mock_response.text = "禁止访问"
        mock_response.request = MagicMock(spec=httpx.Request)
        mock_response.request.url = "https://api.github.com/repos/owner/repo/readme"

        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.get.side_effect = httpx.HTTPStatusError(
            "403 Forbidden", request=mock_response.request, response=mock_response
        )

        with patch('httpx.AsyncClient', return_value=mock_async_client):
            with pytest.raises(HTTPException) as excinfo:
                await github_service.get_readme_content(VALID_GITHUB_URL) # github_service 有一个令牌
            assert excinfo.value.status_code == 403
            assert "检查您的 GITHUB_API_TOKEN 的权限" in excinfo.value.detail
            
    # 使用更复杂的有效 URL 测试 _extract_owner_repo_from_url
    @pytest.mark.parametrize("url, expected_owner, expected_repo", [
        ("https://github.com/user-name/repo-name.git", "user-name", "repo-name"),
        ("https://github.com/user.name/repo.name", "user.name", "repo.name"), # 根据 GitHub，所有者名称不能包含句点，但正则表达式更宽松。我们根据更严格的正则表达式进行测试。
        ("https://github.com/UserName/RepoName", "UserName", "RepoName"),
        ("https://github.com/a/b", "a", "b"), # 短名称
        ("https://github.com/owner/repo-name-with-numbers123", "owner", "repo-name-with-numbers123"),
        ("https://github.com/owner/repo.git.git", "owner", "repo.git"), # 末尾的 .git 被剥离，剩下一个 .git。
    ])
    def test_extract_owner_repo_from_url_more_valid_cases(self, github_service: GithubService, url, expected_owner, expected_repo):
        # 当前所有者的正则表达式: ^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$
        # 当前仓库的正则表达式: ^[a-zA-Z0-9_.-]{1,100}$
        # 所有者的 "user.name" 情况将无法通过所有者正则表达式。这是正确的。
        if "." in expected_owner:
             with pytest.raises(ValueError) as excinfo:
                github_service._extract_owner_repo_from_url(url)
             assert "无效的所有者名称格式" in str(excinfo.value)
        else:
            owner, repo = github_service._extract_owner_repo_from_url(url)
            assert owner == expected_owner
            assert repo == expected_repo

    @pytest.mark.parametrize("invalid_url_for_regex_specifics", [
        ("https://github.com/-owner/repo"), # 所有者以连字符开头
        ("https://github.com/owner-/repo"), # 所有者以连字符结尾
        ("https://github.com/owner/repo..name"), # 仓库包含 ..
        ("https://github.com/owner/.repo"), # 仓库以 . 开头 (GitHub 允许，但当前仓库的正则表达式不允许以 - 或 . 开头)
        ("https://github.com/owner/-repo"), # 仓库以 - 开头
    ])
    def test_extract_owner_repo_from_url_regex_edge_cases(self, github_service: GithubService, invalid_url_for_regex_specifics):
        with pytest.raises(ValueError) as excinfo:
            github_service._extract_owner_repo_from_url(invalid_url_for_regex_specifics)
        # 检查它是否是 ValueError，具体消息取决于哪个部分失败
        assert "无效的所有者名称格式" in str(excinfo.value) or "无效的仓库名称格式" in str(excinfo.value)

    @pytest.mark.parametrize("url_with_subpath", [
        ("https://github.com/owner/repo/issues"),
        ("https://github.com/owner/repo/pulls/1"),
        ("https://github.com/owner/repo/blob/main/README.md"),
    ])
    def test_extract_owner_repo_from_url_handles_subpaths(self, github_service: GithubService, url_with_subpath):
        # 正则表达式 `^https://github\.com/([a-zA-Z0-9.-]+)/([a-zA-Z0-9_.-]+)`
        # 应正确捕获 "owner" 和 "repo"，并忽略子路径。
        owner, repo = github_service._extract_owner_repo_from_url(url_with_subpath)
        assert owner == "owner"
        assert repo == "repo"

    @pytest.mark.asyncio
    async def test_get_readme_content_invalid_url_passed_to_readme_fetch(self, github_service: GithubService):
        # 测试如果 _extract_owner_repo_from_url 失败，get_readme_content 是否引发 HTTPException
        invalid_url = "htp://badurl.com"
        with pytest.raises(HTTPException) as excinfo:
            await github_service.get_readme_content(invalid_url)
        assert excinfo.value.status_code == 400
        assert "无效的 GitHub 仓库 URL" in excinfo.value.detail
