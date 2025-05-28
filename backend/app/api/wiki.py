from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl

# Import the new TaskService
from app.services.task_service import TaskService
# Import the request schema for repository URL
from app.schemas.github import RepositoryRequest 

router = APIRouter()

# --- Pydantic Models for this endpoint ---
class TaskCreationResponse(BaseModel):
    task_id: str
    message: str
    repo_url: HttpUrl

# --- Dependency Injection for Services ---
def get_task_service():
    # This assumes TaskService() can be initialized without arguments,
    # or that its dependencies (like Celery app) are globally available or configured within TaskService.
    return TaskService()

# --- API Endpoints ---
@router.post("/generate", response_model=TaskCreationResponse, summary="Trigger Wiki Generation Task")
async def trigger_wiki_generation(
    repo_request: RepositoryRequest,
    task_service: TaskService = Depends(get_task_service)
):
    """
    Accepts a GitHub repository URL and triggers a background task to generate a Wiki for it.
    Returns the ID of the dispatched task.
    """
    repo_url_str = str(repo_request.url)
    
    task_id = task_service.create_wiki_generation_task(repo_url=repo_url_str)
    
    if not task_id:
        # This implies an issue with Celery setup or task dispatching within TaskService
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to create wiki generation task for repository: {repo_url_str}. Celery might be misconfigured or the task function unavailable."
        )
        
    return TaskCreationResponse(
        task_id=task_id,
        message="Wiki generation task successfully created.",
        repo_url=repo_request.url
    )

# The existing GET /{repo_id} endpoint is a mock.
# A real implementation would use WikiService to fetch generated content.
# For now, per instructions, focusing on /generate.
# Marking the old one as deprecated.
@router.get("/{repo_id}", deprecated=True, summary="Mock endpoint for fetching Wiki (Not Implemented with New Services)")
async def get_wiki_content_mock(repo_id: str):
    """
    Mock endpoint to get Wiki content.
    A real implementation would use WikiService.
    """
    # This is a placeholder and does not use the new services.
    raise HTTPException(status_code=501, detail="Fetching wiki content by repo_id is not fully implemented with new services yet. Use /generate to start generation and /status/{task_id} to check progress.")

# TODO: Implement an endpoint to retrieve the actual wiki content once generated.
# This would likely involve:
# 1. A new method in WikiService, e.g., `get_generated_wiki(repo_url: str)` or `get_wiki_by_task_id(task_id: str)`.
# 2. This service method would check task status (if using task_id) and then retrieve
#    the stored wiki content (e.g., from a database or file system, based on where the
#    Celery `generate_wiki_task` stores its output).
# 3. A new Pydantic response model for the wiki content.