import logging
from fastapi import HTTPException
from typing import Dict, Any, Optional, List

# Ensure agents.pipelines.query_pipeline is accessible.
# Adjust import path if project structure demands it.
from agents.pipelines.query_pipeline import QueryPipeline
from haystack.document_stores import BaseDocumentStore # For type hinting
from haystack.schema import Document # For type hinting, representing retrieved documents

# Configure logging
logger = logging.getLogger(__name__)
# Application-level logging configuration should be done elsewhere (e.g., main app setup)
# For example: logging.basicConfig(level=logging.INFO)

class QueryService:
    def __init__(self, document_store: Optional[BaseDocumentStore] = None):
        """
        Initializes the QueryService.
        The QueryPipeline is instantiated here. If the pipeline requires a document_store
        at initialization (e.g., for a retriever to be configured), it should be passed.

        Args:
            document_store: An optional Haystack DocumentStore instance.
                            The QueryPipeline in `agents.pipelines.query_pipeline.py`
                            is designed to accept this.
        """
        try:
            self.query_pipeline = QueryPipeline(document_store=document_store)
            logger.info("QueryService: QueryPipeline initialized successfully.")
        except Exception as e:
            logger.exception("QueryService: Critical error during QueryPipeline initialization.")
            # This is a critical failure; the service cannot function.
            raise RuntimeError(f"QueryService: Failed to initialize QueryPipeline: {str(e)}")

    def answer_question(self, repo_url: str, question: str) -> Dict[str, Any]:
        """
        Answers a user's question related to a specific repository URL.
        The repo_url is used to filter documents in the document store.

        Args:
            repo_url: The URL of the GitHub repository, used for filtering relevant documents.
            question: The user's question.

        Returns:
            A dictionary containing the question, repository URL, answer, and source documents.
            Example:
            {
                "query": "What is X?",
                "repo_url": "https://github.com/user/repo",
                "answer": "X is a framework for...",
                "documents": [
                    {"content": "...", "meta": {"file_path": "README.md", ...}}, ...
                ]
            }

        Raises:
            HTTPException: For invalid input or if the querying process encounters an error.
        """
        if not question or question.strip() == "":
            logger.warning(f"QueryService: Received an empty or whitespace-only question for repo_url: {repo_url}.")
            raise HTTPException(status_code=400, detail="Question cannot be empty.")
        
        if not repo_url or repo_url.strip() == "": # Also validate repo_url
            logger.warning(f"QueryService: Received an empty or whitespace-only repo_url for question: {question}.")
            raise HTTPException(status_code=400, detail="Repository URL cannot be empty.")

        logger.info(f"QueryService: Processing question for repo_url '{repo_url}': '{question}'")

        try:
            # Prepare the input for the QueryPipeline.
            # The pipeline's `run` method expects `query` and `filters`.
            # The `filters` dictionary should specify the `repo_url` to scope the search.
            # This assumes documents in the DocumentStore have `repo_url` in their metadata.
            pipeline_params = {
                "query": question,
                "filters": {"repo_url": repo_url} 
                # Add other optional params like top_k if needed by pipeline.run and desired here
                # "top_k_retriever": 5, # example
            }
            
            logger.debug(f"QueryService: Invoking QueryPipeline with parameters: {pipeline_params}")
            # The `data` argument for pipeline.run() is typically used when the first component
            # in the pipeline expects specific named inputs that are not 'query' or 'filters'.
            # query_pipeline.py's run method directly takes query, filters etc. as arguments.
            # So, we unpack pipeline_params.
            pipeline_output = self.query_pipeline.run(**pipeline_params)
            logger.debug(f"QueryService: Received output from QueryPipeline: {pipeline_output}")

            if not pipeline_output:
                logger.error(f"QueryService: QueryPipeline returned empty or None output. Repo: '{repo_url}', Question: '{question}'.")
                raise HTTPException(status_code=500, detail="Query pipeline did not return any output.")

            # Extract answer and documents based on the known output structure of QueryPipeline.
            # From `agents/pipelines/query_pipeline.py`:
            # - LLM's reply: `pipeline_output['llm']['replies'][0]`
            # - Retrieved documents: `pipeline_output['retriever']['documents']`
            
            llm_output = pipeline_output.get("llm", {})
            answer_list = llm_output.get("replies", [])
            answer = answer_list[0].strip() if answer_list and isinstance(answer_list[0], str) else None

            retriever_output = pipeline_output.get("retriever", {})
            source_documents = retriever_output.get("documents", [])
            
            # Convert Haystack Document objects to a more API-friendly dict format
            # This makes the service's response serializable and decouples it from Haystack's internal Document class.
            formatted_documents = []
            for doc in source_documents:
                if isinstance(doc, Document):
                    formatted_doc = {
                        "content": doc.content,
                        "meta": doc.meta,
                        # "id": doc.id, # Optional, if needed by frontend
                        # "score": doc.score # Optional, if retriever provides scores and they are useful
                    }
                    formatted_documents.append(formatted_doc)
                else:
                    logger.warning(f"QueryService: Encountered non-Document object in retriever output: {type(doc)}")


            if answer is None:
                # If LLM provides no answer, it might be appropriate to say so.
                # This could also be a 404 if no answer means "not found".
                logger.info(f"QueryService: No direct answer found by LLM. Repo: '{repo_url}', Question: '{question}'.")
                answer = "Could not find a direct answer to your question. However, relevant documents were retrieved."
                if not formatted_documents:
                     answer = "Sorry, I could not find an answer or any relevant documents for your question."


            logger.info(f"QueryService: Successfully processed question. Repo: '{repo_url}'. Answer generated: {bool(answer and 'Sorry' not in answer)}")
            
            return {
                "query": question,
                "repo_url": repo_url,
                "answer": answer,
                "documents": formatted_documents 
            }
            
        except HTTPException: # Re-raise if it's an HTTPException we've thrown
            raise
        except Exception as e:
            logger.exception(f"QueryService: An unexpected error occurred during query processing. Repo: '{repo_url}', Question: '{question}'.")
            # Avoid leaking internal error details to the client unless desired.
            raise HTTPException(status_code=500, detail=f"An error occurred while processing your question: {str(e)}")

# Example of how QueryService might be instantiated and used (e.g., in a FastAPI app):
#
# from haystack.document_stores import InMemoryDocumentStore
# from backend.app.services.query_service import QueryService
#
# # Global or application-scoped document store
# global_document_store = InMemoryDocumentStore(use_bm25=True)
# # ... (populate global_document_store with documents) ...
# # Example:
# # from haystack.schema import Document
# # docs_to_index = [
# #    Document(content="LangChain is a framework.", meta={"repo_url": "https://github.com/langchain-ai/langchain"}),
# #    Document(content="Haystack helps build LLM apps.", meta={"repo_url": "https://github.com/deepset-ai/haystack"})
# # ]
# # global_document_store.write_documents(docs_to_index)
#
# # In a FastAPI route:
# # query_service_instance = QueryService(document_store=global_document_store)
# # result = query_service_instance.answer_question(
# #     repo_url="https://github.com/langchain-ai/langchain",
# #     question="What is LangChain?"
# # )
# # return result