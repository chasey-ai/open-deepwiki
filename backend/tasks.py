import logging
import traceback
from contextlib import contextmanager
from datetime import datetime
from typing import Optional # 从 typing 导入 Optional

from sqlalchemy.orm import Session

# 导入 Celery 应用实例
from .celery_worker import celery_app

# 导入数据库会话和模型
from backend.app.db.session import SessionLocal
from backend.app.db.models import Repository, WikiDocument, Task as DBTask, KnowledgeBase

# 导入服务和管道
from backend.app.services.github_service import GithubService
from backend.app.services.wiki_service import WikiService # WikiService 需要 GithubService
from agents.pipelines.index_pipeline import IndexPipeline
# WikiPipeline 在 WikiService 内部使用，因此此处可能不需要直接导入
# from agents.pipelines.wiki_pipeline import WikiPipeline 

# 配置任务日志
logger = logging.getLogger(__name__)
# 确保您的 Celery worker 配置为输出日志。


@contextmanager
def db_session_scope():
    """围绕一系列操作提供事务作用域。"""
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
    """在数据库中更新任务状态的辅助函数。"""
    try:
        db_task = db.query(DBTask).filter(DBTask.id == task_id).first()
        if db_task:
            db_task.status = status
            if result is not None:
                db_task.result = result 
            if progress is not None:
                db_task.progress = progress
            db_task.updated_at = datetime.utcnow() # 如果数据库有时区，请确保此项具有时区意识
            db.commit()
        else:
            # 任务 {task_id} 在数据库中未找到以更新状态。
            logger.error(f"任务 {task_id} 在数据库中未找到以更新状态。")
    except Exception as e:
        # 更新数据库中任务 {task_id} 状态时出错
        logger.exception(f"更新数据库中任务 {task_id} 状态时出错: {e}")
        db.rollback()


@celery_app.task(bind=True, name="index_repository_task")
def index_repository_task(self, repo_url: str):
    """
    用于索引 GitHub 仓库的 Celery 任务。
    - 使用 GithubService 获取内容。
    - 使用 IndexPipeline 处理和存储内容。
    - 更新数据库中的 Repository、KnowledgeBase 和 Task 模型。
    """
    task_id = self.request.id
    # 任务 {task_id} (index_repository_task) 已为仓库 {repo_url} 启动
    logger.info(f"任务 {task_id} (index_repository_task) 已为仓库 {repo_url} 启动")

    with db_session_scope() as db:
        update_task_status_in_db(db, task_id, "STARTED")

        try:
            # 1. 查找或创建 Repository 条目
            repo_owner, repo_name_from_url = GithubService()._extract_owner_repo_from_url(repo_url) # 用于名称/所有者
            
            repository = db.query(Repository).filter(Repository.url == repo_url).first()
            if not repository:
                repository = Repository(
                    url=repo_url,
                    name=repo_name_from_url, # 提取的名称
                    owner=repo_owner # 提取的所有者
                )
                db.add(repository)
                db.commit() # 提交以获取 repository.id (如果是新的)
                # 任务 {task_id}: 为 {repo_url} 创建了新的 Repository 条目，ID 为 {repository.id}
                logger.info(f"任务 {task_id}: 为 {repo_url} 创建了新的 Repository 条目，ID 为 {repository.id}")
            else:
                # 任务 {task_id}: 找到了 {repo_url} 的现有 Repository 条目，ID 为 {repository.id}
                logger.info(f"任务 {task_id}: 找到了 {repo_url} 的现有 Repository 条目，ID 为 {repository.id}")
            
            # 将任务与仓库关联
            db_task = db.query(DBTask).filter(DBTask.id == task_id).first()
            if db_task:
                db_task.repository_id = repository.id
                db.commit()

            # 2. 实例化 GithubService 和 IndexPipeline
            # IndexPipeline 可能需要一个文档存储，请确保已配置。
            # 本示例假设 IndexPipeline() 处理其自身的文档存储设置
            # 或者有一个全局可用/为 Haystack 配置的文档存储。
            # 如果 IndexPipeline 需要与 `repository.id` 或 `repo_url` 相关的特定 document_store，
            # 则该逻辑需要在此处实现。
            github_service = GithubService() # 从环境中读取令牌
            index_pipeline = IndexPipeline(document_store=None) # 或传递一个已配置的存储

            # 3. 获取仓库内容 (从 README 开始)
            # 任务 {task_id}: 正在为 {repo_url} 获取 README
            logger.info(f"任务 {task_id}: 正在为 {repo_url} 获取 README")
            # self.update_state(state='PROGRESS', meta={'current_step': '获取 README', 'progress': 20})
            update_task_status_in_db(db, task_id, "PROGRESS", progress=20)

            import asyncio
            try:
                readme_content = asyncio.run(github_service.get_readme_content(repo_url))
            except RuntimeError as e:
                if "cannot run current event loop" in str(e): # 已在事件循环中 (例如，如果 worker 是异步的)
                    # 任务 {task_id}: asyncio.run() 失败，可能已在事件循环中。如果 worker 支持，则尝试直接 await。
                    logger.warning(f"任务 {task_id}: asyncio.run() 失败，可能已在事件循环中。如果 worker 支持，则尝试直接 await。")
                    # 这种回退很棘手。如果 worker 是同步的，直接 await 将不起作用。
                    # 如果 worker 是异步的，则任务本身应该是异步的。
                    # 对于同步任务，asyncio.run 是主要方式。
                    # 如果此任务是 `async def`，则将直接使用 `await`。
                    # 这表明任务定义 (同步) 与服务调用 (异步) 之间存在潜在冲突。
                    # 最稳健的解决方案是使调用异步代码的任务成为 `async def`
                    # 并确保 Celery worker 支持它，或者为服务调用使用同步包装器。
                    # 目前，继续使用 asyncio.run 并记录此特定运行时错误。
                    raise # 重新引发以指示问题；需要 worker/任务同步/异步对齐。
                raise # 重新引发其他运行时错误
            
            if not readme_content:
                # 任务 {task_id}: {repo_url} 的 README 为空或未找到。
                logger.warning(f"任务 {task_id}: {repo_url} 的 README 为空或未找到。")
                # 决定这是否是故障或只是过程的一部分
                # 目前，继续进行，但 IndexPipeline 可能会失败或不执行任何操作。

            # 4. 使用 IndexPipeline 处理内容
            # 任务 {task_id}: 正在为 {repo_url} 使用 IndexPipeline 处理内容
            logger.info(f"任务 {task_id}: 正在为 {repo_url} 使用 IndexPipeline 处理内容")
            # self.update_state(state='PROGRESS', meta={'current_step': '正在索引内容', 'progress': 50})
            update_task_status_in_db(db, task_id, "PROGRESS", progress=50)

            # IndexPipeline.run 需要数据: Dict[str, Any]
            # 这应与 IndexPipeline 的输入组件对齐。
            # 假设它需要 "documents"，这些是 Haystack Document 对象或类似对象。
            # 以及用于附加到文档的元数据 "meta" (如 repo_url, source)。
            # 这部分高度依赖于实际的 IndexPipeline 实现。
            # 目前，假设一个简单的情况：
            from haystack.schema import Document as HaystackDocument
            documents_to_index = [
                HaystackDocument(content=readme_content, meta={"source": "README.md", "repo_url": repo_url})
            ]
            if readme_content: # 仅当有内容时运行
                pipeline_result = index_pipeline.run(data={"documents": documents_to_index, "meta": {"repository_id": repository.id, "repo_url": repo_url}})
                # 任务 {task_id}: IndexPipeline 运行完成。结果: {pipeline_result}
                logger.info(f"任务 {task_id}: IndexPipeline 运行完成。结果: {pipeline_result}") # 记录结果以进行调试
            else:
                # 任务 {task_id}: {repo_url} 没有 README 内容可供索引。
                logger.info(f"任务 {task_id}: {repo_url} 没有 README 内容可供索引。")


            # 5. 更新 Repository 和 KnowledgeBase (如果使用)
            repository.last_indexed_at = datetime.utcnow() # 确保具有时区意识
            
            # 如果使用 KnowledgeBase 模型存储路径或 ID:
            kb = db.query(KnowledgeBase).filter(KnowledgeBase.repository_id == repository.id).first()
            if not kb:
                kb = KnowledgeBase(repository_id=repository.id, document_count=len(documents_to_index) if readme_content else 0)
                db.add(kb)
            else:
                kb.document_count = (kb.document_count or 0) + (len(documents_to_index) if readme_content else 0)
                kb.updated_at = datetime.utcnow()
            db.commit()
            
            # 任务 {task_id}: 成功索引仓库 {repo_url}。已更新 Repository 和 KnowledgeBase 条目。
            logger.info(f"任务 {task_id}: 成功索引仓库 {repo_url}。已更新 Repository 和 KnowledgeBase 条目。")
            # 已成功索引 {repo_url}
            update_task_status_in_db(db, task_id, "SUCCESS", result={"message": f"已成功索引 {repo_url}"}, progress=100)
            return {"message": f"已成功索引 {repo_url}", "repository_id": repository.id}

        except Exception as e:
            # 任务 {task_id}: 为 {repo_url} 索引期间出错
            logger.exception(f"任务 {task_id}: 为 {repo_url} 索引期间出错: {e}")
            error_info = {"error": str(e), "traceback": traceback.format_exc()}
            update_task_status_in_db(db, task_id, "FAILURE", result=error_info, progress=0) # 重置进度或设置为当前进度
            # 重新引发异常，以便 Celery 知道任务失败
            raise


@celery_app.task(bind=True, name="generate_wiki_task")
def generate_wiki_task(self, repo_url: str): # 已更改为同步任务
    """
    用于为 GitHub 仓库生成 Wiki 内容的 Celery 任务。
    - 使用 WikiService 生成内容。
    - 将内容存储在 WikiDocument 模型中。
    - 更新 Task 模型状态。
    """
    task_id = self.request.id
    # 任务 {task_id} (generate_wiki_task) 已为仓库 {repo_url} 启动
    logger.info(f"任务 {task_id} (generate_wiki_task) 已为仓库 {repo_url} 启动")

    with db_session_scope() as db:
        update_task_status_in_db(db, task_id, "STARTED")

        try:
            # 1. 查找 Repository 条目 (必须存在，由索引任务或 API 创建)
            repository = db.query(Repository).filter(Repository.url == repo_url).first()
            if not repository:
                # 任务 {task_id}: 未找到 URL 为 {repo_url} 的仓库。Wiki 生成需要现有的仓库条目。
                logger.error(f"任务 {task_id}: 未找到 URL 为 {repo_url} 的仓库。Wiki 生成需要现有的仓库条目。")
                # 未找到仓库 {repo_url}
                update_task_status_in_db(db, task_id, "FAILURE", result={"error": f"未找到仓库 {repo_url}"})
                # 此处不引发异常，让 Celery 将其标记为成功，但在结果中包含错误，
                # 或者如果希望 Celery 将其标记为 FAILED，则引发自定义错误。
                # 为了与 index_repository_task 保持一致，引发错误。
                # 在数据库中未找到位于 {repo_url} 的仓库。
                raise ValueError(f"在数据库中未找到位于 {repo_url} 的仓库。")

            # 如果尚未关联，则将任务与仓库关联
            db_task = db.query(DBTask).filter(DBTask.id == task_id).first()
            if db_task and db_task.repository_id is None:
                db_task.repository_id = repository.id
                db.commit()

            # 2. 实例化 GithubService 和 WikiService
            # WikiService 需要 GithubService。
            github_service = GithubService() # 从环境中读取令牌
            wiki_service = WikiService(github_service=github_service) # WikiService 初始化 WikiPipeline

            # 3. 使用 WikiService 生成 Wiki 内容
            # 任务 {task_id}: 正在使用 WikiService 为 {repo_url} 生成 wiki。
            logger.info(f"任务 {task_id}: 正在使用 WikiService 为 {repo_url} 生成 wiki。")
            # self.update_state(state='PROGRESS', meta={'current_step': '正在生成内容', 'progress': 30})
            update_task_status_in_db(db, task_id, "PROGRESS", progress=30)
            
            import asyncio
            # WikiService.generate_wiki_from_repo_readme 是异步的，因此在事件循环中运行它。
            try:
                generated_content_markdown = asyncio.run(wiki_service.generate_wiki_from_repo_readme(repo_url))
            except RuntimeError as e:
                if "cannot run current event loop" in str(e):
                    # 任务 {task_id}: asyncio.run() 在 generate_wiki_task 中失败，可能已在事件循环中。如果 worker 支持，此任务应为 `async def`，或者服务调用需要同步包装器。
                    logger.error(f"任务 {task_id}: asyncio.run() 在 generate_wiki_task 中失败，可能已在事件循环中。如果 worker 支持，此任务应为 `async def`，或者服务调用需要同步包装器。")
                    raise # 异步/同步 Celery 中的严重配置/设计问题。
                raise
                
            if not generated_content_markdown:
                # 任务 {task_id}: WikiService 未为 {repo_url} 返回任何内容。
                logger.error(f"任务 {task_id}: WikiService 未为 {repo_url} 返回任何内容。")
                # Wiki 生成未返回任何内容。
                update_task_status_in_db(db, task_id, "FAILURE", result={"error": "Wiki 生成未返回任何内容。"})
                raise ValueError("Wiki 生成未返回任何内容。") # 或在适用时作为部分成功处理

            # 4. 将生成的 Wiki 存储在 WikiDocument 模型中
            # 任务 {task_id}: 正在为 {repo_url} 存储生成的 wiki 内容。
            logger.info(f"任务 {task_id}: 正在为 {repo_url} 存储生成的 wiki 内容。")
            # self.update_state(state='PROGRESS', meta={'current_step': '正在存储内容', 'progress': 80})
            update_task_status_in_db(db, task_id, "PROGRESS", progress=80)

            # 检查此仓库是否已存在 WikiDocument
            wiki_doc = db.query(WikiDocument).filter(WikiDocument.repository_id == repository.id).first()
            if wiki_doc:
                # 任务 {task_id}: 正在更新仓库 ID {repository.id} 的现有 WikiDocument
                logger.info(f"任务 {task_id}: 正在更新仓库 ID {repository.id} 的现有 WikiDocument")
                wiki_doc.content_markdown = generated_content_markdown
                wiki_doc.version = (wiki_doc.version or 0) + 1
                wiki_doc.generated_at = datetime.utcnow() # 时区
                wiki_doc.updated_at = datetime.utcnow()
            else:
                # 任务 {task_id}: 正在为仓库 ID {repository.id} 创建新的 WikiDocument
                logger.info(f"任务 {task_id}: 正在为仓库 ID {repository.id} 创建新的 WikiDocument")
                wiki_doc = WikiDocument(
                    repository_id=repository.id,
                    content_markdown=generated_content_markdown,
                    generated_at=datetime.utcnow(), # 时区
                    version=1
                )
                db.add(wiki_doc)
            
            db.commit() # 提交 WikiDocument 更改
            
            # 任务 {task_id}: 已成功为 {repo_url} 生成并存储 wiki。
            logger.info(f"任务 {task_id}: 已成功为 {repo_url} 生成并存储 wiki。")
            # 已成功为 {repo_url} 生成 wiki
            update_task_status_in_db(db, task_id, "SUCCESS", result={"message": f"已成功为 {repo_url} 生成 wiki", "wiki_document_id": wiki_doc.id}, progress=100)
            return {"message": f"已成功为 {repo_url} 生成 wiki", "wiki_document_id": wiki_doc.id}

        except Exception as e:
            # 任务 {task_id}: 为 {repo_url} 生成 wiki 期间出错
            logger.exception(f"任务 {task_id}: 为 {repo_url} 生成 wiki 期间出错: {e}")
            error_info = {"error": str(e), "traceback": traceback.format_exc()}
            update_task_status_in_db(db, task_id, "FAILURE", result=error_info, progress=0)
            raise

# 为了确保在使用 @shared_task 或为了清晰起见与 @celery_app.task 一起使用时注册任务：
# 此文件 (`backend.tasks`) 应包含在 `celery_app.conf.include` 中
# 这已在 `backend/celery_worker.py` 中完成：`include=["backend.tasks"]`
# 因此，这些任务应在 Celery worker 启动时注册。