from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from datetime import datetime

class RepositoryRequest(BaseModel):
    """Request model for providing a GitHub repository URL."""
    url: HttpUrl = Field(..., description="The URL of the GitHub repository.")
    
class RepositoryBaseInfo(BaseModel):
    """Base model for repository information."""
    id: str = Field(..., description="Unique identifier for the repository (e.g., 'owner_name').")
    url: str = Field(..., description="URL of the repository.")
    name: str = Field(..., description="Name of the repository.")
    owner: str = Field(..., description="Owner of the repository.")
    description: Optional[str] = Field(None, description="Description of the repository.")
    
class RepositoryResponse(RepositoryBaseInfo):
    """Response model for repository processing tasks."""
    task_id: str = Field(..., description="ID of the task initiated for repository processing.")
    status: str = Field(..., description="Current status of the task.")
    message: str = Field(..., description="A message related to the task status.")
    
    class Config:
        orm_mode = True

class RepositoryDetail(RepositoryBaseInfo):
    """Detailed repository information including timestamps."""
    created_at: datetime = Field(..., description="Timestamp of when the repository record was created.")
    updated_at: datetime = Field(..., description="Timestamp of when the repository record was last updated.")
    
    class Config:
        orm_mode = True