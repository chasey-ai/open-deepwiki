import logging
from celery.result import AsyncResult
from typing import Dict, Any, Optional

# Attempt to import Celery app and tasks.
# In a real setup, celery_app might be in celery_worker.py or a dedicated celery_setup.py
# and tasks would be in backend.tasks.py.
try:
    from backend.tasks import celery_app, index_repository_task, generate_wiki_task
    # Ensure that these are actual Celery task functions.
    # If they are not defined in backend.tasks, these will be None.
except ImportError:
    logging.warning(
        "TaskService: Could not import Celery app or tasks from backend.tasks. "
        "Task creation and monitoring will not function. "
        "Ensure Celery is configured and `celery_app`, `index_repository_task`, "
        "and `generate_wiki_task` are defined in `backend.tasks.py`."
    )
    celery_app = None
    index_repository_task = None
    generate_wiki_task = None

logger = logging.getLogger(__name__)
# Application-level logging configuration should be handled in the app's entry point.

class TaskService:
    def __init__(self):
        """
        Initializes the TaskService.
        Checks if the Celery application instance is available.
        """
        if not celery_app:
            # This is a critical issue if tasks are expected to work.
            logger.critical(
                "TaskService: Celery application (`celery_app`) is not imported or available. "
                "Task functionality will be disabled."
            )
            # Depending on strictness, could raise RuntimeError here.
            # For this exercise, we'll allow initialization but methods will guard.

    def _dispatch_task(self, task_function, task_args: tuple, task_kwargs: dict, task_name: str) -> Optional[str]:
        """
        Helper to dispatch a Celery task and handle common logic.
        """
        if not celery_app or not task_function:
            logger.error(
                f"TaskService: Cannot dispatch '{task_name}'. Celery app or task function is unavailable. "
                f"Celery App ready: {bool(celery_app)}, Task Function ready: {bool(task_function)}."
            )
            return None
        
        try:
            # task_function.delay(*args, **kwargs) is a shortcut for send_task with default routing.
            # Using apply_async for more control if needed, but delay is fine for simple cases.
            task_instance = task_function.apply_async(args=task_args, kwargs=task_kwargs)
            task_id = task_instance.id
            
            logger.info(f"TaskService: Dispatched '{task_name}' with ID '{task_id}'. Args: {task_args}, Kwargs: {task_kwargs}.")
            
            # Simulate initial database write for the task
            # In a real system: models.Task.create(id=task_id, name=task_name, status='PENDING', params={...})
            logger.info(f"DB_SIMULATION: Task '{task_id}' (Name: '{task_name}') created with status PENDING.")
            
            return task_id
        except Exception as e:
            logger.exception(f"TaskService: Exception during dispatch of '{task_name}'.")
            return None # Or raise a service-specific exception / HTTPException

    def create_indexing_task(self, repo_url: str) -> Optional[str]:
        """
        Dispatches a Celery task to index a repository.

        Args:
            repo_url: The URL of the repository to be indexed.

        Returns:
            The Celery task ID if successfully dispatched, otherwise None.
        """
        if not index_repository_task:
             logger.error("TaskService: `index_repository_task` is not available. Cannot create indexing task.")
             return None
        return self._dispatch_task(
            task_function=index_repository_task,
            task_args=(), # No positional arguments for index_repository_task if it only takes repo_url as kwarg
            task_kwargs={"repo_url": repo_url},
            task_name="repository_indexing"
        )

    def create_wiki_generation_task(self, repo_url: str) -> Optional[str]:
        """
        Dispatches a Celery task to generate a wiki for a repository.

        Args:
            repo_url: The URL of the repository for which to generate a wiki.

        Returns:
            The Celery task ID if successfully dispatched, otherwise None.
        """
        if not generate_wiki_task:
            logger.error("TaskService: `generate_wiki_task` is not available. Cannot create wiki generation task.")
            return None
        return self._dispatch_task(
            task_function=generate_wiki_task,
            task_args=(), # No positional arguments for generate_wiki_task
            task_kwargs={"repo_url": repo_url},
            task_name="wiki_generation"
        )

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Retrieves the status and result of a Celery task.

        Args:
            task_id: The ID of the Celery task.

        Returns:
            A dictionary with task_id, status, and result.
            Status can be PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED.
            Result contains return value on SUCCESS, or Exception info on FAILURE.
        """
        if not celery_app:
            logger.error(f"TaskService: Celery app unavailable. Cannot get status for task '{task_id}'.")
            return {"task_id": task_id, "status": "UNKNOWN", "result": "Celery connection error."}

        try:
            async_result = AsyncResult(task_id, app=celery_app)
            status = async_result.status
            result_data = async_result.result # Could be return value or Exception

            if async_result.failed():
                # Result is an Exception object or traceback
                result_value = f"Failure: {str(result_data)}"
            elif async_result.successful():
                # Result is the task's return value
                result_value = result_data
            else:
                # Task is PENDING, STARTED, RETRY, REVOKED
                result_value = None # Or some placeholder like "Task in progress" or details from task.info

            # Simulate database read/update for task status
            # In a real system: db_task = models.Task.get(id=task_id); db_task.update(status=status, result=result_value)
            logger.info(f"DB_SIMULATION: Task '{task_id}' status is '{status}'. Result available: {result_data is not None}.")

            return {
                "task_id": task_id,
                "status": status,
                "result": result_value, # This will be None if task is not finished
                # Optionally include more details if available from async_result.info
                "details": async_result.info if hasattr(async_result, 'info') else None 
            }
        except Exception as e:
            logger.exception(f"TaskService: Exception while fetching status for task '{task_id}'.")
            return {"task_id": task_id, "status": "ERROR_FETCHING_STATUS", "result": str(e)}

# Example of how TaskService might be used (conceptual):
# if __name__ == "__main__":
#     # This requires backend.tasks.py to have celery_app and task definitions,
#     # and a running Celery broker (e.g., Redis, RabbitMQ) and worker.
#     logging.basicConfig(level=logging.INFO)
#
#     # --- Mock backend.tasks.py for standalone testing ---
#     # from celery import Celery
#     # import time
#     # celery_app = Celery('mock_tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')
#     # @celery_app.task(bind=True)
#     # def index_repository_task(self, repo_url: str):
#     #     self.update_state(state='STARTED', meta={'progress': 0})
#     #     logger.info(f"[TASK] Indexing {repo_url}...")
#     #     time.sleep(3) # Simulate work
#     #     self.update_state(state='PROGRESS', meta={'progress': 50})
#     #     time.sleep(3)
#     #     logger.info(f"[TASK] Indexing {repo_url} complete.")
#     #     return f"Successfully indexed {repo_url}"
#     # @celery_app.task(bind=True)
#     # def generate_wiki_task(self, repo_url: str):
#     #     self.update_state(state='STARTED', meta={'action': 'generating wiki'})
#     #     logger.info(f"[TASK] Generating wiki for {repo_url}...")
#     #     time.sleep(2)
#     #     if "fail" in repo_url:
#     #         logger.error(f"[TASK] Simulating failure for wiki generation: {repo_url}")
#     #         raise ValueError("Simulated wiki generation error")
#     #     logger.info(f"[TASK] Wiki for {repo_url} generated.")
#     #     return f"Wiki content for {repo_url}"
#     # --- End Mock backend.tasks.py ---
#
#     task_service = TaskService()
#     if not celery_app:
#         logger.warning("Celery app not configured. TaskService example will not dispatch tasks.")
#     else:
#         logger.info("Dispatching example tasks...")
#         idx_task_id = task_service.create_indexing_task("https://github.com/example/repo1")
#         wiki_task_id = task_service.create_wiki_generation_task("https://github.com/example/repo2")
#         fail_wiki_task_id = task_service.create_wiki_generation_task("https://github.com/example/repo-fail")
#
#         if idx_task_id: logger.info(f"Indexing task ID: {idx_task_id}")
#         if wiki_task_id: logger.info(f"Wiki task ID: {wiki_task_id}")
#         if fail_wiki_task_id: logger.info(f"Failing Wiki task ID: {fail_wiki_task_id}")
#
#         logger.info("Waiting for a few seconds before checking status (tasks run in background)...")
#         import time
#         time.sleep(8) # Give tasks time to run/complete/fail
#
#         if idx_task_id: logger.info(f"Status for {idx_task_id}: {task_service.get_task_status(idx_task_id)}")
#         if wiki_task_id: logger.info(f"Status for {wiki_task_id}: {task_service.get_task_status(wiki_task_id)}")
#         if fail_wiki_task_id: logger.info(f"Status for {fail_wiki_task_id}: {task_service.get_task_status(fail_wiki_task_id)}")
#
#         # Example of a non-existent task
#         logger.info(f"Status for non_existent_task: {task_service.get_task_status('non-existent-task-id')}")