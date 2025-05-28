from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl

# 导入新的 TaskService
from app.services.task_service import TaskService
# 导入仓库 URL 的请求 schema
from app.schemas.github import RepositoryRequest 

router = APIRouter()

# --- 此端点的 Pydantic 模型 ---
class TaskCreationResponse(BaseModel):
    task_id: str
    message: str
    repo_url: HttpUrl

# --- 服务依赖注入 ---
def get_task_service():
    # 假设 TaskService() 可以在没有参数的情况下初始化，
    # 或者其依赖项 (如 Celery 应用) 是全局可用或在 TaskService 内部配置的。
    """提供 TaskService 的实例。"""
    return TaskService()

# --- API 端点 ---
@router.post("/generate", response_model=TaskCreationResponse, summary="触发 Wiki 生成任务")
async def trigger_wiki_generation(
    repo_request: RepositoryRequest,
    task_service: TaskService = Depends(get_task_service)
):
    """
    接受一个 GitHub 仓库 URL，并触发一个后台任务来为其生成 Wiki。
    返回已分派任务的 ID。
    """
    repo_url_str = str(repo_request.url)
    
    task_id = task_service.create_wiki_generation_task(repo_url=repo_url_str)
    
    if not task_id:
        # 这意味着 TaskService 中的 Celery 设置或任务分派存在问题
        # 为仓库创建 wiki 生成任务失败: {repo_url_str}。Celery 可能配置错误或任务函数不可用。
        raise HTTPException(
            status_code=500, 
            detail=f"为仓库 {repo_url_str} 创建 wiki 生成任务失败。Celery 可能配置错误或任务函数不可用。"
        )
        
    return TaskCreationResponse(
        task_id=task_id,
        message="Wiki 生成任务已成功创建。", # Wiki generation task successfully created.
        repo_url=repo_request.url
    )

# 现有的 GET /{repo_id} 端点是一个模拟端点。
# 真正的实现将使用 WikiService 来获取生成的内容。
# 目前，根据指示，专注于 /generate 端点。
# 将旧端点标记为已弃用。
@router.get("/{repo_id}", deprecated=True, summary="获取 Wiki 的模拟端点 (尚未使用新服务实现)")
async def get_wiki_content_mock(repo_id: str):
    """
    获取 Wiki 内容的模拟端点。
    真正的实现将使用 WikiService。
    """
    # 这是一个占位符，不使用新服务。
    # 通过 repo_id 获取 wiki 内容的功能尚未使用新服务完全实现。请使用 /generate 开始生成，并使用 /status/{task_id} 检查进度。
    raise HTTPException(status_code=501, detail="通过 repo_id 获取 wiki 内容的功能尚未使用新服务完全实现。请使用 /generate 开始生成，并使用 /status/{task_id} 检查进度。")

# TODO: 实现一个端点以在生成后检索实际的 wiki 内容。
# 这可能涉及：
# 1. WikiService 中的一个新方法，例如 `get_generated_wiki(repo_url: str)` 或 `get_wiki_by_task_id(task_id: str)`。
# 2. 此服务方法将检查任务状态 (如果使用 task_id)，然后检索
#    存储的 wiki 内容 (例如，从数据库或文件系统，取决于
#    Celery `generate_wiki_task` 存储其输出的位置)。
# 3. wiki 内容的新 Pydantic 响应模型。