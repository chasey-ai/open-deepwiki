import logging
import traceback
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy.orm import Session

# Import Celery app instance
from .celery_worker import celery_app

# Import database session and models
from backend.app.db.session import SessionLocal
from backend.app.db.models import Repository, WikiDocument, Task as DBTask, KnowledgeBase

# Import services and pipelines
from backend.app.services.github_service import GithubService
from backend.app.services.wiki_service import WikiService # WikiService needs GithubService
from agents.pipelines.index_pipeline import IndexPipeline
# WikiPipeline is used internally by WikiService, so direct import here might not be needed
# from agents.pipelines.wiki_pipeline import WikiPipeline 

# Configure logging for tasks
logger = logging.getLogger(__name__)
# Ensure your Celery worker is configured to output logs.


@contextmanager
def db_session_scope():
    """Provide a transactional scope around a series of operations."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def update_task_status_in_db(db: Session, task_id: str, status: str, result: Optional[dict] = None, progress: Optional[int] = None):
    """Helper function to update task status in the database."""
    try:
        db_task = db.query(DBTask).filter(DBTask.id == task_id).first()
        if db_task:
            db_task.status = status
            if result is not None:
                db_task.result = result 
            if progress is not None:
                db_task.progress = progress
            db_task.updated_at = datetime.utcnow() # Ensure this is timezone-aware if DB is
            db.commit()
        else:
            logger.error(f"Task {task_id} not found in DB for status update.")
    except Exception as e:
        logger.exception(f"Error updating task {task_id} status in DB: {e}")
        db.rollback()


@celery_app.task(bind=True, name="index_repository_task")
def index_repository_task(self, repo_url: str):
    """
    Celery task to index a GitHub repository.
    - Fetches content using GithubService.
    - Processes and stores content using IndexPipeline.
    - Updates Repository, KnowledgeBase, and Task models in the database.
    """
    task_id = self.request.id
    logger.info(f"Task {task_id} (index_repository_task) started for repo: {repo_url}")

    with db_session_scope() as db:
        update_task_status_in_db(db, task_id, "STARTED")

        try:
            # 1. Find or Create Repository entry
            repo_owner, repo_name_from_url = GithubService()._extract_owner_repo_from_url(repo_url) # For name/owner
            
            repository = db.query(Repository).filter(Repository.url == repo_url).first()
            if not repository:
                repository = Repository(
                    url=repo_url,
                    name=repo_name_from_url, # Extracted name
                    owner=repo_owner # Extracted owner
                )
                db.add(repository)
                db.commit() # Commit to get repository.id if it's new
                logger.info(f"Task {task_id}: Created new Repository entry for {repo_url} with ID {repository.id}")
            else:
                logger.info(f"Task {task_id}: Found existing Repository entry for {repo_url} with ID {repository.id}")
            
            # Associate task with repository
            db_task = db.query(DBTask).filter(DBTask.id == task_id).first()
            if db_task:
                db_task.repository_id = repository.id
                db.commit()

            # 2. Instantiate GithubService and IndexPipeline
            # IndexPipeline might need a document store, ensure it's configured.
            # For this example, assume IndexPipeline() handles its own document store setup
            # or one is globally available/configured for Haystack.
            # If IndexPipeline expects a specific document_store related to `repository.id` or `repo_url`,
            # that logic would need to be here.
            github_service = GithubService() # Token is read from env
            index_pipeline = IndexPipeline(document_store=None) # Or pass a configured store

            # 3. Fetch repository content (starting with README)
            logger.info(f"Task {task_id}: Fetching README for {repo_url}")
            # self.update_state(state='PROGRESS', meta={'current_step': 'Fetching README', 'progress': 20})
            update_task_status_in_db(db, task_id, "PROGRESS", progress=20)

            import asyncio
            try:
                readme_content = asyncio.run(github_service.get_readme_content(repo_url))
            except RuntimeError as e:
                if "cannot run current event loop" in str(e): # Already in an event loop (e.g. if worker is async)
                    logger.warning(f"Task {task_id}: asyncio.run() failed, possibly already in an event loop. Trying direct await (if worker supports).")
                    # This fallback is tricky. If the worker is sync, direct await won't work.
                    # If worker is async, then the task itself should be async.
                    # For a sync task, asyncio.run is the primary way.
                    # If this task were `async def`, then `await` would be used directly.
                    # This indicates a potential conflict in task definition (sync) vs. service calls (async).
                    # The most robust solution is to make tasks that call async code be `async def`
                    # and ensure the Celery worker supports it, or use a sync wrapper for the service call.
                    # For now, proceeding with asyncio.run and logging this specific runtime error.
                    raise # Re-raise to indicate the problem; needs worker/task sync/async alignment.
                raise # Re-raise other runtime errors
            
            if not readme_content:
                logger.warning(f"Task {task_id}: README for {repo_url} is empty or not found.")
                # Decide if this is a failure or just part of the process
                # For now, proceed, but IndexPipeline might fail or do nothing.

            # 4. Process content with IndexPipeline
            logger.info(f"Task {task_id}: Processing content with IndexPipeline for {repo_url}")
            # self.update_state(state='PROGRESS', meta={'current_step': 'Indexing content', 'progress': 50})
            update_task_status_in_db(db, task_id, "PROGRESS", progress=50)

            # IndexPipeline.run expects data: Dict[str, Any]
            # This should align with IndexPipeline's input component.
            # Assuming it expects "documents" which are Haystack Document objects or similar.
            # And "meta" for metadata to attach to documents (like repo_url, source).
            # This part is highly dependent on the actual IndexPipeline implementation.
            # For now, let's assume a simple case:
            from haystack.schema import Document as HaystackDocument
            documents_to_index = [
                HaystackDocument(content=readme_content, meta={"source": "README.md", "repo_url": repo_url})
            ]
            if readme_content: # Only run if there's content
                pipeline_result = index_pipeline.run(data={"documents": documents_to_index, "meta": {"repository_id": repository.id, "repo_url": repo_url}})
                logger.info(f"Task {task_id}: IndexPipeline run completed. Result: {pipeline_result}") # Log result for debug
            else:
                logger.info(f"Task {task_id}: No README content to index for {repo_url}.")


            # 5. Update Repository and KnowledgeBase (if used)
            repository.last_indexed_at = datetime.utcnow() # Ensure this is timezone-aware
            
            # If KnowledgeBase model is used to store path or ID:
            kb = db.query(KnowledgeBase).filter(KnowledgeBase.repository_id == repository.id).first()
            if not kb:
                kb = KnowledgeBase(repository_id=repository.id, document_count=len(documents_to_index) if readme_content else 0)
                db.add(kb)
            else:
                kb.document_count = (kb.document_count or 0) + (len(documents_to_index) if readme_content else 0)
                kb.updated_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"Task {task_id}: Successfully indexed repository {repo_url}. Updated Repository and KnowledgeBase entries.")
            update_task_status_in_db(db, task_id, "SUCCESS", result={"message": f"Successfully indexed {repo_url}"}, progress=100)
            return {"message": f"Successfully indexed {repo_url}", "repository_id": repository.id}

        except Exception as e:
            logger.exception(f"Task {task_id}: Error during indexing for {repo_url}: {e}")
            error_info = {"error": str(e), "traceback": traceback.format_exc()}
            update_task_status_in_db(db, task_id, "FAILURE", result=error_info, progress=0) # Reset progress or set to current
            # Re-raise the exception so Celery knows the task failed
            raise


@celery_app.task(bind=True, name="generate_wiki_task")
def generate_wiki_task(self, repo_url: str): # Changed to sync task
    """
    Celery task to generate Wiki content for a GitHub repository.
    - Uses WikiService to generate content.
    - Stores content in WikiDocument model.
    - Updates Task model status.
    """
    task_id = self.request.id
    logger.info(f"Task {task_id} (generate_wiki_task) started for repo: {repo_url}")

    with db_session_scope() as db:
        update_task_status_in_db(db, task_id, "STARTED")

        try:
            # 1. Find Repository entry (must exist, created by indexing task or API)
            repository = db.query(Repository).filter(Repository.url == repo_url).first()
            if not repository:
                logger.error(f"Task {task_id}: Repository not found for URL {repo_url}. Wiki generation requires an existing repository entry.")
                update_task_status_in_db(db, task_id, "FAILURE", result={"error": f"Repository not found for {repo_url}"})
                # Do not raise here, let Celery mark as success but with error in result,
                # or raise custom error if preferred for Celery to mark as FAILED.
                # For consistency with index_repository_task, raising an error.
                raise ValueError(f"Repository at {repo_url} not found in database.")

            # Associate task with repository if not already
            db_task = db.query(DBTask).filter(DBTask.id == task_id).first()
            if db_task and db_task.repository_id is None:
                db_task.repository_id = repository.id
                db.commit()

            # 2. Instantiate GithubService and WikiService
            # WikiService needs GithubService.
            github_service = GithubService() # Token from env
            wiki_service = WikiService(github_service=github_service) # WikiService initializes WikiPipeline

            # 3. Generate Wiki content using WikiService
            logger.info(f"Task {task_id}: Generating wiki for {repo_url} using WikiService.")
            # self.update_state(state='PROGRESS', meta={'current_step': 'Generating content', 'progress': 30})
            update_task_status_in_db(db, task_id, "PROGRESS", progress=30)
            
            import asyncio
            # WikiService.generate_wiki_from_repo_readme is async, so run it in an event loop.
            try:
                generated_content_markdown = asyncio.run(wiki_service.generate_wiki_from_repo_readme(repo_url))
            except RuntimeError as e:
                if "cannot run current event loop" in str(e):
                    logger.error(f"Task {task_id}: asyncio.run() failed in generate_wiki_task, possibly already in an event loop. This task should be `async def` if worker supports it, or the service call needs a sync wrapper.")
                    raise # Critical configuration/design issue for async in sync Celery.
                raise
                
            if not generated_content_markdown:
                logger.error(f"Task {task_id}: WikiService returned no content for {repo_url}.")
                update_task_status_in_db(db, task_id, "FAILURE", result={"error": "Wiki generation returned no content."})
                raise ValueError("Wiki generation returned no content.") # Or handle as partial success if applicable

            # 4. Store generated Wiki in WikiDocument model
            logger.info(f"Task {task_id}: Storing generated wiki content for {repo_url}.")
            # self.update_state(state='PROGRESS', meta={'current_step': 'Storing content', 'progress': 80})
            update_task_status_in_db(db, task_id, "PROGRESS", progress=80)

            # Check if a WikiDocument already exists for this repository
            wiki_doc = db.query(WikiDocument).filter(WikiDocument.repository_id == repository.id).first()
            if wiki_doc:
                logger.info(f"Task {task_id}: Updating existing WikiDocument for repository ID {repository.id}")
                wiki_doc.content_markdown = generated_content_markdown
                wiki_doc.version = (wiki_doc.version or 0) + 1
                wiki_doc.generated_at = datetime.utcnow() # Timezone
                wiki_doc.updated_at = datetime.utcnow()
            else:
                logger.info(f"Task {task_id}: Creating new WikiDocument for repository ID {repository.id}")
                wiki_doc = WikiDocument(
                    repository_id=repository.id,
                    content_markdown=generated_content_markdown,
                    generated_at=datetime.utcnow(), # Timezone
                    version=1
                )
                db.add(wiki_doc)
            
            db.commit() # Commit WikiDocument changes
            
            logger.info(f"Task {task_id}: Successfully generated and stored wiki for {repo_url}.")
            update_task_status_in_db(db, task_id, "SUCCESS", result={"message": f"Successfully generated wiki for {repo_url}", "wiki_document_id": wiki_doc.id}, progress=100)
            return {"message": f"Successfully generated wiki for {repo_url}", "wiki_document_id": wiki_doc.id}

        except Exception as e:
            logger.exception(f"Task {task_id}: Error during wiki generation for {repo_url}: {e}")
            error_info = {"error": str(e), "traceback": traceback.format_exc()}
            update_task_status_in_db(db, task_id, "FAILURE", result=error_info, progress=0)
            raise

# To ensure tasks are registered if using @shared_task or for clarity with @celery_app.task:
# This file (`backend.tasks`) should be included in `celery_app.conf.include`
# which is already done in `backend/celery_worker.py`: `include=["backend.tasks"]`
# So, these tasks should be registered when the Celery worker starts.