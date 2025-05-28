import base64
import httpx
import os
import re # 用于更健壮的URL解析和验证

from fastapi import HTTPException

class GithubService:
    def __init__(self):
        self.github_api_token = os.getenv("GITHUB_API_TOKEN")
        # 此处不在实际服务代码中打印警告，应由应用配置日志处理
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self.github_api_token:
            self.headers["Authorization"] = f"token {self.github_api_token}"

    async def get_readme_content(self, repo_url: str) -> str:
        """
        获取指定 GitHub 仓库 URL 的主 README.md 文件内容。

        参数:
            repo_url: GitHub 仓库的 URL (例如："https://github.com/owner/repo")。

        返回:
            README.md 文件的内容字符串。

        引发:
            HTTPException: 如果仓库 URL 无效、仓库未找到、README 未找到或发生其他 API 错误。
        """
        try:
            owner, repo = self._extract_owner_repo_from_url(repo_url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"无效的 GitHub 仓库 URL: {e}")

        readme_api_url = f"https://api.github.com/repos/{owner}/{repo}/readme"

        async with httpx.AsyncClient(timeout=10.0) as client: # 添加了超时
            try:
                response = await client.get(readme_api_url, headers=self.headers)
                response.raise_for_status()
            except httpx.TimeoutException:
                # 请求 GitHub API 超时。
                raise HTTPException(status_code=408, detail="请求 GitHub API 超时。")
            except httpx.RequestError as exc:
                # 广泛的网络相关错误
                # 服务不可用：连接 GitHub API 时出错
                raise HTTPException(status_code=503, detail=f"服务不可用：连接 GitHub API 时出错: {exc}")
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                if status_code == 404:
                    # 在仓库 '{owner}/{repo}' 中未找到 README，或者仓库本身未找到。
                    raise HTTPException(status_code=404, detail=f"在仓库 '{owner}/{repo}' 中未找到 README，或者仓库本身未找到。")
                elif status_code == 403:
                    # 禁止访问 GitHub API。
                    detail_msg = "禁止访问 GitHub API。"
                    if not self.github_api_token:
                        # GITHUB_API_TOKEN 未设置或未提供。公共仓库可能可以访问，但私有仓库需要令牌。
                        detail_msg += "GITHUB_API_TOKEN 未设置或未提供。公共仓库可能可以访问，但私有仓库需要令牌。"
                    else:
                        # 检查您的 GITHUB_API_TOKEN 对此仓库的权限。
                        detail_msg += "检查您的 GITHUB_API_TOKEN 对此仓库的权限。"
                    raise HTTPException(status_code=403, detail=detail_msg)
                elif status_code == 401: # 未授权 - 通常与令牌问题的403类似
                     # 未授权访问 GitHub API。请确保您的 GITHUB_API_TOKEN 有效。
                     raise HTTPException(status_code=401, detail="未授权访问 GitHub API。请确保您的 GITHUB_API_TOKEN 有效。")
                else:
                    # 常规 GitHub API 错误
                    # GitHub API 错误
                    raise HTTPException(status_code=status_code, detail=f"GitHub API 错误 ({status_code}): {exc.response.text}")

        data = response.json()
        
        if "content" not in data or not data["content"]:
            # 如果 README 不存在，此情况理论上应由 /readme 端点的 404 捕获
            # 在 '{owner}/{repo}' 的 API 响应中未找到 README 内容或是空的。
            raise HTTPException(status_code=404, detail=f"在 '{owner}/{repo}' 的 API 响应中未找到 README 内容或是空的。")

        readme_content_base64 = data["content"]
        try:
            readme_content = base64.b64decode(readme_content_base64).decode("utf-8")
        except (ValueError, TypeError, base64.binascii.Error) as e: # 更具体的解码异常
            # 从 Base64 解码 README 内容时出错
            raise HTTPException(status_code=500, detail=f"从 Base64 解码 README 内容时出错: {e}")
            
        return readme_content

    def _extract_owner_repo_from_url(self, repo_url: str) -> tuple[str, str]:
        """
        从 GitHub 仓库 URL 中提取所有者和仓库名称。
        处理各种 GitHub URL 格式。
        示例: "https://github.com/owner/repo" -> ("owner", "repo")
                 "https://github.com/owner/repo.git" -> ("owner", "repo")
                 "https://github.com/owner/repo/tree/main" -> ("owner", "repo")
        """
        if not isinstance(repo_url, str):
            # 仓库 URL 必须是字符串。
            raise ValueError("仓库 URL 必须是字符串。")

        # 用于从各种 GitHub URL 格式中捕获所有者和仓库的正则表达式
        # 涵盖:
        # - https://github.com/owner/repo
        # - https://github.com/owner/repo.git
        # - https://github.com/owner/repo/ (带末尾斜杠)
        # - https://github.com/owner/repo/tree/branch
        # - https://github.com/owner/repo/blob/branch/file.md
        # 不匹配:
        # - 没有 https://github.com/ 前缀的 URL
        # - 无效的所有者/仓库名称 (GitHub 有特定规则，但我们进行基本检查)
        match = re.match(r"^https://github\.com/([a-zA-Z0-9.-]+)/([a-zA-Z0-9_.-]+)", repo_url)
        
        if not match:
            # 无效的 GitHub 仓库 URL 格式。预期格式：'https://github.com/owner/repo'。
            raise ValueError("无效的 GitHub 仓库 URL 格式。预期格式：'https://github.com/owner/repo'。")
        
        owner, repo = match.group(1), match.group(2)

        if not owner: # 理论上应由正则表达式捕获，但作为安全措施
            # URL 中的所有者不能为空。
            raise ValueError("URL 中的所有者不能为空。")
        if not repo: # 理论上应由正则表达式捕获
            # URL 中的仓库名称不能为空。
            raise ValueError("URL 中的仓库名称不能为空。")
        
        # GitHub 仓库名称可以以 .git 结尾，如果存在则移除以保持一致性
        if repo.endswith(".git"):
            repo = repo[:-4]
            
        # 对所有者和仓库名称进行基本验证 (字母数字、连字符、下划线，仓库名称可包含句点)
        # GitHub 规则:
        # 所有者：字母数字和连字符。不能以连字符开头/结尾。最多39个字符。
        # 仓库：字母数字、连字符、下划线、句点。最多100个字符。
        # 此正则表达式对所有者更宽松，允许句点。
        # 无效的所有者名称格式: '{owner}'。所有者只能包含字母数字字符和连字符，且不能以连字符开头或结尾。
        if not re.fullmatch(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$", owner):
             raise ValueError(f"无效的所有者名称格式: '{owner}'。所有者只能包含字母数字字符和连字符，且不能以连字符开头或结尾。")
        # 无效的仓库名称格式: '{repo}'。仓库名称可以包含字母数字字符、连字符、句点和下划线，但不能包含 '..' 或以连字符开头。
        if not re.fullmatch(r"^[a-zA-Z0-9_.-]{1,100}$", repo) or ".." in repo or repo.startswith("-"):
             raise ValueError(f"无效的仓库名称格式: '{repo}'。仓库名称可以包含字母数字字符、连字符、句点和下划线，但不能包含 '..' 或以连字符开头。")

        return owner, repo

# 示例用法 (如果需要，用于本地测试)
# if __name__ == "__main__":
#     import asyncio
# 
#     async def test_service():
#         # 重要提示：设置 GITHUB_API_TOKEN 环境变量以确保此测试可靠运行
#         # export GITHUB_API_TOKEN="your_personal_access_token"
#         if not os.getenv("GITHUB_API_TOKEN"):
#             print("警告：未设置 GITHUB_API_TOKEN。测试可能会失败或受到速率限制。") # WARNING: GITHUB_API_TOKEN is not set. Tests might fail or be rate-limited.
# 
#         service = GithubService()
#         
#         test_urls = [
#             ("Valid public repo", "https://github.com/octocat/Hello-World"),
#             ("Valid public repo with .git", "https://github.com/octocat/Spoon-Knife.git"),
#             ("Valid public repo with trailing slash", "https://github.com/openai/gpt-3/"),
#             ("Valid public repo with branch path", "https://github.com/microsoft/vscode/tree/main"),
#             ("Repo that might not have a README", "https://github.com/twbs/bootstrap"), # 假设 bootstrap 有一个
#             ("Non-existent repo", "https://github.com/this-user-does-not-exist/this-repo-does-not-exist-either"),
#             ("Invalid URL format", "https://github.com/justowner"),
#             ("Non-GitHub URL", "https://example.com/owner/repo"),
#             ("URL with invalid owner chars!!", "https://github.com/owner!!!/repo"),
#             ("URL with invalid repo chars<>", "https://github.com/owner/repo<>"),
#             ("URL with owner starting with hyphen", "https://github.com/-owner/repo"),
#             ("URL with repo starting with hyphen", "https://github.com/owner/-repo"),
#             ("URL with repo containing ..", "https://github.com/owner/repo..name"),
#             ("URL with .git in the middle of repo name", "https://github.com/owner/my.git.repo"), # 这是有效的仓库名称
#             ("URL with owner having period", "https://github.com/my.owner/repo"), # 无效的所有者名称
#         ]
# 
#         for description, url in test_urls:
#             print(f"\n--- 测试中: {description} ({url}) ---") # Testing
#             try:
#                 # 首先测试提取
#                 owner, repo_name = service._extract_owner_repo_from_url(url)
#                 print(f"已提取: Owner='{owner}', Repo='{repo_name}'") # Extracted
#                 
#                 # 然后测试 get_readme_content
#                 # 对于此测试块中已知的无效所有者/仓库解析，跳过 README 获取
#                 # 跳过获取具有故意无效 URL 结构的 README。
#                 if "invalid owner chars" in description or "invalid repo chars" in description or \
#                    "owner starting with hyphen" in description or "repo containing .." in description or \
#                    "owner having period" in description:
#                     print("跳过获取具有故意无效 URL 结构的 README。") # Skipping README fetch for intentionally invalid URL structure.
#                     continue
#                 
#                 readme = await service.get_readme_content(url)
#                 print(f"README (前 100 个字符): {readme[:100].replace('\n', ' ')}...") # README (first 100 chars)
#             except HTTPException as e:
#                 print(f"HTTP 错误: {e.detail} (状态码: {e.status_code})") # HTTP Error, Status
#             except ValueError as e:
#                 print(f"值错误: {e}") # Validation Error
#             except Exception as e:
#                 print(f"意外错误: {type(e).__name__} - {e}") # Unexpected Error
# 
#     # if os.getenv("GITHUB_API_TOKEN"):
#     #    asyncio.run(test_service())
#     # else:
#     #    print("跳过 test_service 运行，因为未设置 GITHUB_API_TOKEN。") # Skipping test_service run as GITHUB_API_TOKEN is not set.
#
# # 供应用程序使用的单个实例 (FastAPI 依赖注入会更好地处理这个问题)
# # github_service_instance = GithubService()