from fastapi import APIRouter, HTTPException, Depends, Path
from pydantic import BaseModel, Field
from typing import Any, Optional

# Import the new TaskService
from app.services.task_service import TaskService

router = APIRouter()

# --- Pydantic Models for this endpoint ---
class TaskStatusDetailResponse(BaseModel):
    task_id: str = Field(..., description="The ID of the Celery task.")
    status: str = Field(..., description="The current status of the task (e.g., PENDING, SUCCESS, FAILURE).")
    result: Optional[Any] = Field(None, description="The result of the task if completed, or error details if failed.")
    details: Optional[Any] = Field(None, description="Additional details or metadata about the task's progress.")

# --- Dependency Injection for Services ---
def get_task_service():
    # Assumes TaskService can be initialized without arguments,
    # or its dependencies (like Celery app) are globally available/configured.
    return TaskService()

# --- API Endpoints ---
@router.get("/{task_id}", response_model=TaskStatusDetailResponse, summary="Get Celery Task Status")
async def get_celery_task_status(
    task_id: str = Path(..., description="The ID of the Celery task to query.", min_length=1),
    task_service: TaskService = Depends(get_task_service)
):
    """
    Retrieves the status, result, and details of a Celery task
    by its ID.
    """
    if not task_id or task_id.isspace():
        # Path validation should catch this, but as a safeguard.
        raise HTTPException(status_code=400, detail="Task ID cannot be empty.")
        
    try:
        # TaskService.get_task_status returns a dict:
        # {"task_id": str, "status": str, "result": Any, "details": Any}
        status_info = task_service.get_task_status(task_id=task_id)
        
        # The TaskService might return a status like "UNKNOWN" or "ERROR_FETCHING_STATUS"
        # if Celery connection fails or other issues occur within the service.
        # These are valid states to return to the client.
        if status_info.get("status") == "UNKNOWN" and "Celery connection error" in str(status_info.get("result")):
             # Potentially map this to a 503 Service Unavailable if Celery is down
             pass # For now, return as is from service.

        return TaskStatusDetailResponse(**status_info)
        
    except Exception as e:
        # This would catch unexpected errors in this endpoint handler itself,
        # not errors from within TaskService that are already handled and returned.
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while fetching task status: {str(e)}")