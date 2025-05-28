from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class TaskBase(BaseModel):
    """Base model for a task."""
    id: str = Field(..., description="Unique ID of the task (often the Celery task ID).")
    task_type: str = Field(..., description="Type of the task (e.g., 'index', 'wiki_generation').")
    status: str = Field(..., description="Current status of the task (e.g., 'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED').")
    
class TaskStatusResponse(TaskBase):
    """Response model for task status inquiries (potentially simplified)."""
    # This model might be used by endpoints that return a more summarized task status.
    # The /api/status/{task_id} endpoint uses TaskStatusDetailResponse defined in status.py,
    # which is more aligned with TaskService.get_task_status output.
    # This TaskStatusResponse can be kept if other parts of the system use it,
    # or deprecated/removed if TaskStatusDetailResponse is preferred globally.
    progress: int = Field(0, description="Task progress percentage (0-100).")
    message: Optional[str] = Field(None, description="A message related to the task's current status or outcome.")
    result_url: Optional[str] = Field(None, description="URL to retrieve the result of the task, if applicable.")
    
    class Config:
        orm_mode = True
        
class TaskDetail(TaskBase):
    """Detailed information about a task, often corresponding to the database model."""
    # This model seems more aligned with the DB `Task` model.
    repository_id: Optional[str] = Field(None, description="ID of the repository associated with the task, if any.")
    # celery_task_id: Optional[str] = Field(None, description="Celery's internal task ID, if different from the main 'id'.") 
    # -> Task.id in DB is now the Celery task ID, so this field is redundant.
    progress: int = Field(0, description="Task progress percentage.")
    message: Optional[str] = Field(None, description="Status message.")
    result: Optional[Dict[str, Any]] = Field(None, description="Result of the task, or error details if failed (JSON format).")
    created_at: datetime = Field(..., description="Timestamp when the task record was created.")
    updated_at: datetime = Field(..., description="Timestamp when the task record was last updated.")
    
    class Config:
        orm_mode = True