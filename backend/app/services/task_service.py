import logging
from celery.result import AsyncResult
from typing import Dict, Any, Optional

# 尝试导入 Celery 应用和任务。
# 在实际设置中，celery_app 可能位于 celery_worker.py 或专用的 celery_setup.py 中，
# 任务则位于 backend.tasks.py。
try:
    from backend.tasks import celery_app, index_repository_task, generate_wiki_task
    # 确保这些是实际的 Celery 任务函数。
    # 如果它们没有在 backend.tasks 中定义，这些将为 None。
except ImportError:
    logging.warning(
        "TaskService: 无法从 backend.tasks 导入 Celery 应用或任务。"
        "任务创建和监控将无法运行。"
        "请确保 Celery 已配置，并且 `celery_app`、`index_repository_task` "
        "和 `generate_wiki_task` 已在 `backend.tasks.py` 中定义。"
    )
    celery_app = None
    index_repository_task = None
    generate_wiki_task = None

logger = logging.getLogger(__name__)
# 应用级别的日志配置应在应用的入口点处理。

class TaskService:
    def __init__(self):
        """
        初始化 TaskService。
        检查 Celery 应用实例是否可用。
        """
        if not celery_app:
            # 如果期望任务工作，这是一个严重问题。
            logger.critical(
                "TaskService: Celery 应用 (`celery_app`) 未导入或不可用。"
                "任务功能将被禁用。"
            )
            # 根据严格程度，此处可引发 RuntimeError。
            # 对于本练习，我们允许初始化，但方法将进行保护。

    def _dispatch_task(self, task_function, task_args: tuple, task_kwargs: dict, task_name: str) -> Optional[str]:
        """
        分派 Celery 任务并处理通用逻辑的辅助函数。
        """
        if not celery_app or not task_function:
            logger.error(
                # TaskService: 无法分派 '{task_name}'。Celery 应用或任务函数不可用。
                # Celery 应用就绪: {bool(celery_app)}, 任务函数就绪: {bool(task_function)}.
                f"TaskService: 无法分派 '{task_name}'。Celery 应用或任务函数不可用。"
                f"Celery 应用就绪: {bool(celery_app)}, 任务函数就绪: {bool(task_function)}。"
            )
            return None
        
        try:
            # task_function.delay(*args, **kwargs) 是 send_task 使用默认路由的快捷方式。
            # 如果需要更多控制，可使用 apply_async，但对于简单情况，delay 也可以。
            task_instance = task_function.apply_async(args=task_args, kwargs=task_kwargs)
            task_id = task_instance.id
            
            # TaskService: 已分派 '{task_name}'，ID 为 '{task_id}'。参数: {task_args}, 关键字参数: {task_kwargs}.
            logger.info(f"TaskService: 已分派 '{task_name}'，ID 为 '{task_id}'。参数: {task_args}, 关键字参数: {task_kwargs}。")
            
            # 模拟任务创建的初始数据库写入
            # 在实际系统中: models.Task.create(id=task_id, name=task_name, status='PENDING', params={...})
            # 数据库模拟：任务 '{task_id}' (名称: '{task_name}') 已创建，状态为 PENDING。
            logger.info(f"数据库模拟：任务 '{task_id}' (名称: '{task_name}') 已创建，状态为 PENDING。")
            
            return task_id
        except Exception as e:
            # TaskService: 分派 '{task_name}' 期间发生异常。
            logger.exception(f"TaskService: 分派 '{task_name}' 期间发生异常。")
            return None # 或引发特定于服务的异常 / HTTPException

    def create_indexing_task(self, repo_url: str) -> Optional[str]:
        """
        分派一个 Celery 任务来索引仓库。

        参数:
            repo_url: 要索引的仓库 URL。

        返回:
            如果成功分派，则为 Celery 任务 ID，否则为 None。
        """
        if not index_repository_task:
             # TaskService: `index_repository_task` 不可用。无法创建索引任务。
             logger.error("TaskService: `index_repository_task` 不可用。无法创建索引任务。")
             return None
        return self._dispatch_task(
            task_function=index_repository_task,
            task_args=(), # 如果 index_repository_task 仅将 repo_url 作为关键字参数，则无位置参数
            task_kwargs={"repo_url": repo_url},
            task_name="repository_indexing"
        )

    def create_wiki_generation_task(self, repo_url: str) -> Optional[str]:
        """
        分派一个 Celery 任务来为仓库生成 wiki。

        参数:
            repo_url: 要为其生成 wiki 的仓库 URL。

        返回:
            如果成功分派，则为 Celery 任务 ID，否则为 None。
        """
        if not generate_wiki_task:
            # TaskService: `generate_wiki_task` 不可用。无法创建 wiki 生成任务。
            logger.error("TaskService: `generate_wiki_task` 不可用。无法创建 wiki 生成任务。")
            return None
        return self._dispatch_task(
            task_function=generate_wiki_task,
            task_args=(), # generate_wiki_task 没有位置参数
            task_kwargs={"repo_url": repo_url},
            task_name="wiki_generation"
        )

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        检索 Celery 任务的状态和结果。

        参数:
            task_id: Celery 任务的 ID。

        返回:
            包含 task_id、status 和 result 的字典。
            状态可以是 PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED。
            Result 包含 SUCCESS 时的返回值，或 FAILURE 时的异常信息。
        """
        if not celery_app:
            # TaskService: Celery 应用不可用。无法获取任务 '{task_id}' 的状态。
            # Celery 连接错误。
            logger.error(f"TaskService: Celery 应用不可用。无法获取任务 '{task_id}' 的状态。")
            return {"task_id": task_id, "status": "UNKNOWN", "result": "Celery 连接错误。"}

        try:
            async_result = AsyncResult(task_id, app=celery_app)
            status = async_result.status
            result_data = async_result.result # 可能是返回值或异常

            if async_result.failed():
                # Result 是一个 Exception 对象或追溯信息
                # 失败
                result_value = f"失败: {str(result_data)}"
            elif async_result.successful():
                # Result 是任务的返回值
                result_value = result_data
            else:
                # 任务处于 PENDING, STARTED, RETRY, REVOKED 状态
                result_value = None # 或类似 "任务进行中" 的占位符或来自 task.info 的详细信息

            # 模拟任务状态的数据库读取/更新
            # 在实际系统中: db_task = models.Task.get(id=task_id); db_task.update(status=status, result=result_value)
            # 数据库模拟：任务 '{task_id}' 的状态是 '{status}'。结果可用: {result_data is not None}.
            logger.info(f"数据库模拟：任务 '{task_id}' 的状态是 '{status}'。结果可用: {result_data is not None}。")

            return {
                "task_id": task_id,
                "status": status,
                "result": result_value, # 如果任务未完成，此项将为 None
                # 如果可用，可选择性地包含来自 async_result.info 的更多详细信息
                "details": async_result.info if hasattr(async_result, 'info') else None 
            }
        except Exception as e:
            # TaskService: 获取任务 '{task_id}' 状态时发生异常。
            logger.exception(f"TaskService: 获取任务 '{task_id}' 状态时发生异常。")
            return {"task_id": task_id, "status": "ERROR_FETCHING_STATUS", "result": str(e)}

# TaskService 可能如何使用的示例 (概念性):
# if __name__ == "__main__":
#     # 这需要 backend.tasks.py 具有 celery_app 和任务定义，
#     # 以及正在运行的 Celery broker (例如 Redis, RabbitMQ) 和 worker。
#     logging.basicConfig(level=logging.INFO)
#
#     # --- 用于独立测试的模拟 backend.tasks.py ---
#     # from celery import Celery
#     # import time
#     # celery_app = Celery('mock_tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')
#     # @celery_app.task(bind=True)
#     # def index_repository_task(self, repo_url: str):
#     #     self.update_state(state='STARTED', meta={'progress': 0})
#     #     logger.info(f"[任务] 正在索引 {repo_url}...") # [TASK] Indexing {repo_url}...
#     #     time.sleep(3) # 模拟工作
#     #     self.update_state(state='PROGRESS', meta={'progress': 50})
#     #     time.sleep(3)
#     #     logger.info(f"[任务] {repo_url} 索引完成。") # [TASK] Indexing {repo_url} complete.
#     #     return f"已成功索引 {repo_url}" # Successfully indexed {repo_url}
#     # @celery_app.task(bind=True)
#     # def generate_wiki_task(self, repo_url: str):
#     #     self.update_state(state='STARTED', meta={'action': 'generating wiki'})
#     #     logger.info(f"[任务] 正在为 {repo_url} 生成 wiki...") # [TASK] Generating wiki for {repo_url}...
#     #     time.sleep(2)
#     #     if "fail" in repo_url:
#     #         logger.error(f"[任务] 模拟 wiki 生成失败: {repo_url}") # [TASK] Simulating failure for wiki generation: {repo_url}
#     #         raise ValueError("模拟的 wiki 生成错误") # Simulated wiki generation error
#     #     logger.info(f"[任务] {repo_url} 的 wiki 已生成。") # [TASK] Wiki for {repo_url} generated.
#     #     return f"{repo_url} 的 Wiki 内容" # Wiki content for {repo_url}
#     # --- 模拟 backend.tasks.py 结束 ---
#
#     task_service = TaskService()
#     if not celery_app:
#         logger.warning("Celery 应用未配置。TaskService 示例将不分派任务。") # Celery app not configured. TaskService example will not dispatch tasks.
#     else:
#         logger.info("正在分派示例任务...") # Dispatching example tasks...
#         idx_task_id = task_service.create_indexing_task("https://github.com/example/repo1")
#         wiki_task_id = task_service.create_wiki_generation_task("https://github.com/example/repo2")
#         fail_wiki_task_id = task_service.create_wiki_generation_task("https://github.com/example/repo-fail")
#
#         if idx_task_id: logger.info(f"索引任务 ID: {idx_task_id}") # Indexing task ID
#         if wiki_task_id: logger.info(f"Wiki 任务 ID: {wiki_task_id}") # Wiki task ID
#         if fail_wiki_task_id: logger.info(f"失败的 Wiki 任务 ID: {fail_wiki_task_id}") # Failing Wiki task ID
#
#         logger.info("等待几秒钟以检查状态 (任务在后台运行)...") # Waiting for a few seconds before checking status (tasks run in background)...
#         import time
#         time.sleep(8) # 给任务一些时间运行/完成/失败
#
#         if idx_task_id: logger.info(f"{idx_task_id} 的状态: {task_service.get_task_status(idx_task_id)}") # Status for {idx_task_id}
#         if wiki_task_id: logger.info(f"{wiki_task_id} 的状态: {task_service.get_task_status(wiki_task_id)}") # Status for {wiki_task_id}
#         if fail_wiki_task_id: logger.info(f"{fail_wiki_task_id} 的状态: {task_service.get_task_status(fail_wiki_task_id)}") # Status for {fail_wiki_task_id}
#
#         # 不存在的任务示例
#         logger.info(f"不存在的任务状态: {task_service.get_task_status('non-existent-task-id')}") # Status for non_existent_task