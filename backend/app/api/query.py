from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Dict, Any, Optional

# Import the new QueryService
from app.services.query_service import QueryService
# Import Haystack DocumentStore for dependency injection, if QueryService requires it directly
# from haystack.document_stores import BaseDocumentStore

router = APIRouter()

# --- Pydantic Models for this endpoint ---
class AskQueryRequest(BaseModel):
    repo_url: HttpUrl = Field(..., description="The URL of the GitHub repository to query against.")
    question: str = Field(..., min_length=1, description="The question to ask about the repository.")

class FormattedSourceDocument(BaseModel):
    content: str
    meta: Dict[str, Any] = Field(default_factory=dict)
    # id: Optional[str] = None # Uncomment if needed
    # score: Optional[float] = None # Uncomment if needed

class AskQueryResponse(BaseModel):
    query: str
    repo_url: HttpUrl
    answer: str
    documents: List[FormattedSourceDocument]

# --- Dependency Injection for Services ---
def get_query_service():
    """
    Provides an instance of QueryService.
    If QueryService required a DocumentStore at initialization, it would be provided here.
    Example:
    from backend.app.db.document_store_instance import get_document_store # Hypothetical
    doc_store = get_document_store()
    return QueryService(document_store=doc_store)
    """
    # My QueryService implementation allows document_store=None,
    # assuming QueryPipeline handles its own store or uses a default.
    return QueryService(document_store=None) 

# --- API Endpoints ---
@router.post("/ask", response_model=AskQueryResponse, summary="Ask a question about a repository")
async def ask_question_about_repository(
    request: AskQueryRequest,
    query_service: QueryService = Depends(get_query_service)
):
    """
    Accepts a GitHub repository URL and a question, then returns an answer
    based on the repository's indexed content, along with source documents.
    """
    try:
        repo_url_str = str(request.repo_url)
        # The QueryService's answer_question method returns a dictionary:
        # {"query": str, "repo_url": str, "answer": str, "documents": List[FormattedDocument]}
        # where FormattedDocument is {"content": str, "meta": dict}
        result_dict = query_service.answer_question(repo_url=repo_url_str, question=request.question)
        
        # Ensure the structure matches AskQueryResponse, especially 'documents'
        # The service already formats documents into dicts {content: str, meta: dict}
        return AskQueryResponse(
            query=result_dict["query"],
            repo_url=HttpUrl(result_dict["repo_url"]), # Ensure it's HttpUrl type
            answer=result_dict["answer"],
            documents=[FormattedSourceDocument(**doc) for doc in result_dict["documents"]]
        )
        
    except HTTPException as e:
        # Forward HTTPExceptions raised by the service (e.g., for invalid input to service)
        raise e
    except ValueError as ve: # Catch Pydantic validation errors if HttpUrl conversion fails
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(ve)}")
    except Exception as e:
        # Catch any other unexpected errors during the process
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while processing the query: {str(e)}")

# The old root POST endpoint in query.py was a mock.
# It's replaced by the more specific "/ask" endpoint.