from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Response

# Import current services and schemas
from app.schemas.github import RepositoryRequest, RepositoryResponse
# Assuming the new GithubService is in app.services.github_service
# and the old one is also named github_service (which might be an instance).
# To avoid confusion, let's be specific with imports.
from app.services.github_service import GithubService as NewGithubService # The one I implemented
from app.services.task_service import TaskService # The one I implemented

# The existing code uses an instance `github_service` and `task_service`.
# For the new endpoint, I'll use dependency injection for NewGithubService.
# If the existing endpoint /repository is to be kept and uses old services,
# we need to ensure they are available or refactor it.
# For now, I'll assume the existing `github_service` and `task_service` instances
# are from the old implementation and leave them for the existing endpoint.

router = APIRouter()

# Dependency for the new GithubService
def get_new_github_service():
    return NewGithubService()

# Dependency for the new TaskService (if needed by the old endpoint, it should be updated)
# For now, assuming the old endpoint uses an older TaskService instance if `task_service` is one.
# If `task_service` is an instance of the new TaskService, that's fine.
# Let's assume `task_service` refers to an instance of the new `TaskService`.
# If not, the old endpoint might need adjustment or its own DI.
# For clarity, let's assume the old endpoint needs to be updated or removed if services clash.
# For this task, I will focus on adding the NEW /readme endpoint.
# I'll keep the old `/repository` endpoint as is, assuming its dependencies are met by existing instances.
# If `app.services.github_service.github_service` is the OLD instance, the existing endpoint is fine.
# If `app.services.task_service.task_service` is the NEW instance, the existing endpoint might be fine.

# This is the existing endpoint, I will leave it as is.
# It seems to use `github_service.validate_repository_url` and `extract_repo_info`
# which are not part of the NewGithubService I wrote (it has _extract_owner_repo_from_url).
# This implies `app.services.github_service.github_service` is an OLD service instance.
# And `app.services.task_service.task_service` is also an OLD service instance (it has `create_task`).
# My new TaskService has `create_indexing_task` etc.
# This means the old endpoint /repository is incompatible with my new services without a refactor.
# For the scope of "implement the API endpoints", I should focus on making the new ones work
# with the new services. The old /repository endpoint might need to be addressed separately.

# For now, I'll assume the global `github_service` and `task_service` are the old ones.
from app.services.github_service import github_service as old_github_service_instance
from app.services.task_service import task_service as old_task_service_instance


@router.post("/repository", response_model=RepositoryResponse, deprecated=True, summary="Old endpoint, consider for removal or refactor")
async def process_repository(
    repo_request: RepositoryRequest,
    background_tasks: BackgroundTasks
):
    """
    Receives GitHub repository URL, starts processing. (OLD IMPLEMENTATION)
    """
    if not old_github_service_instance.validate_repository_url(str(repo_request.url)):
        raise HTTPException(status_code=400, detail="Invalid GitHub repository URL")
    
    try:
        repo_info = old_github_service_instance.extract_repo_info(str(repo_request.url))
        # The old task_service.create_task("index", repo_info["id"]) is different from the new TaskService.
        task = old_task_service_instance.create_task("index", repo_info["id"])
        
        # Background task logic (commented out in original)
        # background_tasks.add_task(...)
        
        return {
            **repo_info,
            "task_id": task["id"],
            "status": task["status"],
            "message": task["message"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

# New endpoint for fetching README using the new GithubService
@router.post("/readme", summary="Fetch repository README content")
async def get_repository_readme(
    repo_request: RepositoryRequest,
    service: NewGithubService = Depends(get_new_github_service)
):
    """
    Accepts a GitHub repository URL and returns its README content.
    Uses the new `GithubService` for fetching.
    """
    try:
        readme_content = await service.get_readme_content(str(repo_request.url))
        return Response(content=readme_content, media_type="text/plain")
    except HTTPException as e:
        # Re-raise HTTPException from the service
        raise e
    except Exception as e:
        # Catch any other unexpected errors
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

# TODO: Define a ReadmeResponse Pydantic model in schemas/github.py for a more structured response,
# e.g., class ReadmeResponse(BaseModel): content: str; repo_url: HttpUrl;
# and then use `response_model=ReadmeResponse` in the decorator.
# For now, returning plain text.