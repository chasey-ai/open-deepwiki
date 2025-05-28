from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional

# Note: The new /api/query/ask endpoint uses AskQueryRequest and AskQueryResponse
# defined in backend/app/api/query.py.
# The models below (QueryRequest, QueryResponse, SourceDocument) are the pre-existing ones.
# Their usage should be reviewed; they might be intended for different query mechanisms
# or could be deprecated/refactored.

class QueryRequest(BaseModel):
    """
    Request model for submitting a query.
    Note: The current /api/query/ask uses repo_url. This model uses repository_id.
    Consider standardizing on either repo_url or repository_id.
    """
    repository_id: str = Field(..., description="ID of the repository to query against.")
    query: str = Field(..., description="The user's question.")
    # repo_url: Optional[HttpUrl] = Field(None, description="Alternative: URL of the repository.") # Example if consolidating

class SourceDocument(BaseModel):
    """
    Represents a source document that supports an answer.
    Note: The /api/query/ask endpoint's response model (AskQueryResponse)
    uses a FormattedSourceDocument which has 'content' and 'meta' fields,
    aligning with Haystack Document structure. This SourceDocument model
    has 'text', 'file', 'url'.
    """
    text: str = Field(..., description="Relevant text snippet from the source document.")
    file: Optional[str] = Field(None, description="Filename of the source document.")
    url: Optional[HttpUrl] = Field(None, description="URL to the source document or file.") # Changed to HttpUrl for validation
    
class QueryResponse(BaseModel):
    """
    Response model for a query.
    Note: The /api/query/ask endpoint's response model (AskQueryResponse)
    includes the original query and repo_url, and its document structure is different.
    """
    answer: str = Field(..., description="The generated answer to the query.")
    sources: List[SourceDocument] = Field(..., description="List of source documents that support the answer.")
    
    class Config:
        orm_mode = True