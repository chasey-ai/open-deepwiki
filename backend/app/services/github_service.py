import base64
import httpx
import os
import re # For more robust URL parsing and validation

from fastapi import HTTPException

class GithubService:
    def __init__(self):
        self.github_api_token = os.getenv("GITHUB_API_TOKEN")
        # No warning print here in actual service code, this should be handled by app configuration logging
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self.github_api_token:
            self.headers["Authorization"] = f"token {self.github_api_token}"

    async def get_readme_content(self, repo_url: str) -> str:
        """
        Fetches the main README.md content of a given GitHub repository URL.

        Args:
            repo_url: The URL of the GitHub repository (e.g., "https://github.com/owner/repo").

        Returns:
            The content of the README.md file as a string.

        Raises:
            HTTPException: If the repository URL is invalid, repository is not found, 
                           README is not found, or other API errors occur.
        """
        try:
            owner, repo = self._extract_owner_repo_from_url(repo_url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid GitHub repository URL: {e}")

        readme_api_url = f"https://api.github.com/repos/{owner}/{repo}/readme"

        async with httpx.AsyncClient(timeout=10.0) as client: # Added timeout
            try:
                response = await client.get(readme_api_url, headers=self.headers)
                response.raise_for_status()
            except httpx.TimeoutException:
                raise HTTPException(status_code=408, detail="Request to GitHub API timed out.")
            except httpx.RequestError as exc:
                # Broad network-related error
                raise HTTPException(status_code=503, detail=f"Service unavailable: Error connecting to GitHub API: {exc}")
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                if status_code == 404:
                    raise HTTPException(status_code=404, detail=f"README not found in repository '{owner}/{repo}', or repository itself not found.")
                elif status_code == 403:
                    detail_msg = "Access to GitHub API forbidden. "
                    if not self.github_api_token:
                        detail_msg += "GITHUB_API_TOKEN is not set or provided. Public repositories might be accessible, but private ones require a token."
                    else:
                        detail_msg += "Check your GITHUB_API_TOKEN's permissions for this repository."
                    raise HTTPException(status_code=403, detail=detail_msg)
                elif status_code == 401: # Unauthorized - often similar to 403 for token issues
                     raise HTTPException(status_code=401, detail="Unauthorized access to GitHub API. Ensure your GITHUB_API_TOKEN is valid.")
                else:
                    # General GitHub API error
                    raise HTTPException(status_code=status_code, detail=f"GitHub API error ({status_code}): {exc.response.text}")

        data = response.json()
        
        if "content" not in data or not data["content"]:
            # This case should ideally be caught by 404 on the /readme endpoint if README doesn't exist
            raise HTTPException(status_code=404, detail=f"README content not found or is empty in API response for '{owner}/{repo}'.")

        readme_content_base64 = data["content"]
        try:
            readme_content = base64.b64decode(readme_content_base64).decode("utf-8")
        except (ValueError, TypeError, base64.binascii.Error) as e: # More specific exceptions for decoding
            raise HTTPException(status_code=500, detail=f"Error decoding README content from Base64: {e}")
            
        return readme_content

    def _extract_owner_repo_from_url(self, repo_url: str) -> tuple[str, str]:
        """
        Extracts the owner and repository name from a GitHub repository URL.
        Handles various GitHub URL formats.
        Example: "https://github.com/owner/repo" -> ("owner", "repo")
                 "https://github.com/owner/repo.git" -> ("owner", "repo")
                 "https://github.com/owner/repo/tree/main" -> ("owner", "repo")
        """
        if not isinstance(repo_url, str):
            raise ValueError("Repository URL must be a string.")

        # Regex to capture owner and repo from various GitHub URL formats
        # Covers:
        # - https://github.com/owner/repo
        # - https://github.com/owner/repo.git
        # - https://github.com/owner/repo/ (with trailing slash)
        # - https://github.com/owner/repo/tree/branch
        # - https://github.com/owner/repo/blob/branch/file.md
        # Does not match:
        # - URLs without https://github.com/ prefix
        # - Invalid owner/repo names (GitHub has specific rules, but we do a basic check)
        match = re.match(r"^https://github\.com/([a-zA-Z0-9.-]+)/([a-zA-Z0-9_.-]+)", repo_url)
        
        if not match:
            raise ValueError("Invalid GitHub repository URL format. Expected 'https://github.com/owner/repo'.")
        
        owner, repo = match.group(1), match.group(2)

        if not owner: # Should be caught by regex, but as a safeguard
            raise ValueError("Owner cannot be empty in the URL.")
        if not repo: # Should be caught by regex
            raise ValueError("Repository name cannot be empty in the URL.")
        
        # GitHub repo names can end with .git, remove it if present for consistency
        if repo.endswith(".git"):
            repo = repo[:-4]
            
        # Basic validation for owner and repo names (alphanumeric, hyphens, underscores, periods for repo)
        # GitHub rules:
        # Owner: Alphanumeric and hyphens. Cannot start/end with hyphen. Max 39 chars.
        # Repo: Alphanumeric, hyphens, underscores, periods. Max 100 chars.
        # This regex is a bit more permissive for owner, allowing periods.
        if not re.fullmatch(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$", owner):
             raise ValueError(f"Invalid owner name format: '{owner}'. Owner can only contain alphanumeric characters and hyphens, and cannot start or end with a hyphen.")
        if not re.fullmatch(r"^[a-zA-Z0-9_.-]{1,100}$", repo) or ".." in repo or repo.startswith("-"):
             raise ValueError(f"Invalid repository name format: '{repo}'. Repo name can include alphanumeric characters, hyphens, periods, and underscores, but not '..' or start with a hyphen.")

        return owner, repo

# Example usage (for local testing, if needed)
# if __name__ == "__main__":
#     import asyncio
# 
#     async def test_service():
#         # IMPORTANT: Set GITHUB_API_TOKEN environment variable for this test to work reliably
#         # export GITHUB_API_TOKEN="your_personal_access_token"
#         if not os.getenv("GITHUB_API_TOKEN"):
#             print("WARNING: GITHUB_API_TOKEN is not set. Tests might fail or be rate-limited.")
# 
#         service = GithubService()
#         
#         test_urls = [
#             ("Valid public repo", "https://github.com/octocat/Hello-World"),
#             ("Valid public repo with .git", "https://github.com/octocat/Spoon-Knife.git"),
#             ("Valid public repo with trailing slash", "https://github.com/openai/gpt-3/"),
#             ("Valid public repo with branch path", "https://github.com/microsoft/vscode/tree/main"),
#             ("Repo that might not have a README", "https://github.com/twbs/bootstrap"), # Assuming bootstrap has one
#             ("Non-existent repo", "https://github.com/this-user-does-not-exist/this-repo-does-not-exist-either"),
#             ("Invalid URL format", "https://github.com/justowner"),
#             ("Non-GitHub URL", "https://example.com/owner/repo"),
#             ("URL with invalid owner chars!!", "https://github.com/owner!!!/repo"),
#             ("URL with invalid repo chars<>", "https://github.com/owner/repo<>"),
#             ("URL with owner starting with hyphen", "https://github.com/-owner/repo"),
#             ("URL with repo starting with hyphen", "https://github.com/owner/-repo"),
#             ("URL with repo containing ..", "https://github.com/owner/repo..name"),
#             ("URL with .git in the middle of repo name", "https://github.com/owner/my.git.repo"), # This is valid repo name
#             ("URL with owner having period", "https://github.com/my.owner/repo"), # Invalid owner name
#         ]
# 
#         for description, url in test_urls:
#             print(f"\n--- Testing: {description} ({url}) ---")
#             try:
#                 # Test extraction first
#                 owner, repo_name = service._extract_owner_repo_from_url(url)
#                 print(f"Extracted: Owner='{owner}', Repo='{repo_name}'")
#                 
#                 # Then test get_readme_content
#                 # Skip README fetching for known invalid owner/repo in parsing for this test block
#                 if "invalid owner chars" in description or "invalid repo chars" in description or \
#                    "owner starting with hyphen" in description or "repo containing .." in description or \
#                    "owner having period" in description:
#                     print("Skipping README fetch for intentionally invalid URL structure.")
#                     continue
#                 
#                 readme = await service.get_readme_content(url)
#                 print(f"README (first 100 chars): {readme[:100].replace('\n', ' ')}...")
#             except HTTPException as e:
#                 print(f"HTTP Error: {e.detail} (Status: {e.status_code})")
#             except ValueError as e:
#                 print(f"Validation Error: {e}")
#             except Exception as e:
#                 print(f"Unexpected Error: {type(e).__name__} - {e}")
# 
#     # if os.getenv("GITHUB_API_TOKEN"):
#     #    asyncio.run(test_service())
#     # else:
#     #    print("Skipping test_service run as GITHUB_API_TOKEN is not set.")
#
# # Single instance for the application to use (FastAPI dependency injection will handle this better)
# # github_service_instance = GithubService()