import logging
from fastapi import HTTPException

# Assuming GithubService is in the same directory or accessible via PYTHONPATH
# Adjust the import path based on your project structure if necessary.
# from backend.app.services.github_service import GithubService
# For this specific environment, the path might be different, let's assume:
from .github_service import GithubService # Relative import if in the same package
from agents.pipelines.wiki_pipeline import WikiPipeline 

# Configure logging
logger = logging.getLogger(__name__)
# Ensure logging is configured in your application's entry point or a logging config file.
# For example, logging.basicConfig(level=logging.INFO) if not already set up.

class WikiService:
    def __init__(self, github_service: GithubService):
        """
        Initializes the WikiService with a GithubService instance.
        """
        if not isinstance(github_service, GithubService):
            logger.error(f"Failed to initialize WikiService: github_service is not an instance of GithubService. Type provided: {type(github_service)}")
            raise TypeError("github_service must be an instance of GithubService")
        self.github_service = github_service
        
        try:
            # Initialize the WikiPipeline.
            # This might require configuration (e.g., API keys for LLMs) passed via environment variables
            # or a configuration object, which WikiPipeline's __init__ should handle.
            self.wiki_pipeline = WikiPipeline()
            logger.info("WikiService: WikiPipeline initialized successfully.")
        except Exception as e:
            logger.exception("WikiService: Failed to initialize WikiPipeline.") # Logs traceback
            # This is a critical failure, so the service should not start or indicate it's degraded.
            raise RuntimeError(f"WikiService: Critical component WikiPipeline failed to initialize: {e}")

    async def generate_wiki_from_repo_readme(self, repo_url: str) -> str:
        """
        Generates a wiki page content from the README of a given GitHub repository URL.

        Args:
            repo_url: The URL of the GitHub repository.

        Returns:
            The generated wiki content as a string.

        Raises:
            HTTPException: If fetching the README fails or if the wiki generation process fails.
        """
        logger.info(f"WikiService: Attempting to generate wiki from README for repo: {repo_url}")
        try:
            readme_content = await self.github_service.get_readme_content(repo_url)
            if not readme_content or readme_content.isspace():
                logger.warning(f"WikiService: README content for {repo_url} is empty or whitespace.")
                raise HTTPException(status_code=404, detail=f"README content for {repo_url} is empty or consists only of whitespace. Cannot generate Wiki.")
        except HTTPException as e:
            logger.error(f"WikiService: Error fetching README for {repo_url}: {e.detail} (Status: {e.status_code})")
            # Re-raise the HTTPException from GithubService to be handled by the API layer
            raise e 
        except Exception as e:
            # Catch any other unexpected errors from get_readme_content
            logger.exception(f"WikiService: Unexpected error fetching README for {repo_url}.")
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred while fetching README: {str(e)}")

        logger.info(f"WikiService: Successfully fetched README for {repo_url}. Length: {len(readme_content)} characters.")
        logger.info("WikiService: Invoking WikiPipeline...")

        try:
            # The WikiPipeline.run method expects a dictionary with 'repo_url' and 'repo_summary_markdown'.
            pipeline_input = {"repo_url": repo_url, "repo_summary_markdown": readme_content}
            
            # Assuming WikiPipeline.run is synchronous. If it were async, it would be `await self.wiki_pipeline.run(...)`
            pipeline_output = self.wiki_pipeline.run(data=pipeline_input)
            
            if not pipeline_output:
                logger.error(f"WikiService: WikiPipeline returned empty or None output for {repo_url}.")
                raise HTTPException(status_code=500, detail="Wiki generation pipeline returned no output.")

            # Extract the generated text. Based on `agents/pipelines/wiki_pipeline.py`,
            # the output is a dictionary, and the generated text is in `pipeline_output["text_generator"]["results"][0]`.
            generated_wiki_text = None
            if (isinstance(pipeline_output, dict) and
                "text_generator" in pipeline_output and
                isinstance(pipeline_output["text_generator"], dict) and
                "results" in pipeline_output["text_generator"] and
                isinstance(pipeline_output["text_generator"]["results"], list) and
                len(pipeline_output["text_generator"]["results"]) > 0):
                
                raw_result = pipeline_output["text_generator"]["results"][0]
                # The result might be a string or some object. Ensure it's string.
                if hasattr(raw_result, 'content'): # If it's a Document-like object
                    generated_wiki_text = str(raw_result.content)
                elif isinstance(raw_result, str):
                     generated_wiki_text = raw_result
                else: # Fallback if the structure is different or result is not directly a string
                    generated_wiki_text = str(raw_result)

                if generated_wiki_text:
                    generated_wiki_text = generated_wiki_text.strip()

            if not generated_wiki_text:
                logger.error(f"WikiService: Could not extract generated wiki text from WikiPipeline output for {repo_url}. Raw Output: {pipeline_output}")
                raise HTTPException(status_code=500, detail="Failed to extract content from wiki generation pipeline output.")

            logger.info(f"WikiService: Successfully generated wiki for {repo_url}. Output length: {len(generated_wiki_text)} characters.")
            return generated_wiki_text
            
        except HTTPException: # Re-raise HTTPExceptions explicitly if thrown by pipeline (less likely)
            raise
        except Exception as e:
            logger.exception(f"WikiService: WikiPipeline execution failed for {repo_url}.")
            raise HTTPException(status_code=500, detail=f"Wiki generation process failed: {str(e)}")

# Note: The example usage (main async function) is removed from the service file.
# It should be part of a test suite or an example script, not the service module itself.
# For instantiation in a FastAPI app, dependency injection would typically be used.
# Example (in your FastAPI app setup):
# from backend.app.services.github_service import GithubService
# from backend.app.services.wiki_service import WikiService
# github_serv = GithubService() # Assuming GITHUB_API_TOKEN is set in env
# wiki_serv = WikiService(github_service=github_serv)
# Then use `wiki_serv` in your route handlers.