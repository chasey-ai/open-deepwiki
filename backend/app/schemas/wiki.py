from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime

# Note: The /api/wiki/generate endpoint uses RepositoryRequest from app.schemas.github
# and TaskCreationResponse defined in app.api.wiki.
# The models below might be for other planned Wiki functionalities (e.g., direct retrieval).

class WikiRequest(BaseModel):
    """Request model for Wiki generation (potentially for direct, non-task based generation or specific content)."""
    # This model is not directly used by the current /api/wiki/generate endpoint,
    # which uses RepositoryRequest. If this is for a different purpose, its usage should be clarified.
    repository_url: HttpUrl = Field(..., description="URL of the repository for which to generate/retrieve a Wiki.")
    # repository_id: str = Field(..., description="Repository ID") # Original field, changed to URL for consistency

class NavigationItem(BaseModel):
    """Represents a single item in a Wiki's navigation structure."""
    title: str = Field(..., description="Display title of the navigation item.")
    id: str = Field(..., description="Unique identifier for this navigation item (e.g., for linking).")
    children: Optional[List['NavigationItem']] = Field(None, description="Nested navigation items, if any.")

NavigationItem.update_forward_refs() # For self-referencing 'children'

class WikiContentResponse(BaseModel):
    """Response model for delivering generated Wiki content."""
    repository_url: HttpUrl = Field(..., description="URL of the repository this Wiki belongs to.")
    content_markdown: str = Field(..., description="The generated Wiki content in Markdown format.")
    navigation: Optional[List[NavigationItem]] = Field(None, description="Navigation structure for the Wiki (if available).")
    generated_at: datetime = Field(..., description="Timestamp of when this version of the Wiki was generated.")
    version: int = Field(1, description="Version number of this Wiki document.")
    
    class Config:
        orm_mode = True

# WikiResponse for task creation is handled by TaskCreationResponse in app.api.wiki.py.
# This WikiResponse might be for a different context or can be deprecated.
# class OldWikiTaskResponse(BaseModel):
#     """Response model for a Wiki generation task (might be deprecated)."""
#     task_id: str = Field(..., description="ID of the Wiki generation task.")
#     status: str = Field(..., description="Current status of the task.")
#     message: str = Field(..., description="Message related to the task status.")
    
#     class Config:
#         orm_mode = True