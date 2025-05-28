from fastapi import APIRouter, HTTPException, Depends, Path
from pydantic import BaseModel, Field
from typing import Any, Optional

# 导入新的 TaskService
from app.services.task_service import TaskService

router = APIRouter()

# --- 此端点的 Pydantic 模型 ---
class TaskStatusDetailResponse(BaseModel):
    task_id: str = Field(..., description="Celery 任务的 ID。")
    status: str = Field(..., description="任务的当前状态 (例如, PENDING, SUCCESS, FAILURE)。")
    result: Optional[Any] = Field(None, description="如果任务完成，则为任务结果；如果失败，则为错误详情。")
    details: Optional[Any] = Field(None, description="关于任务进度的附加详情或元数据。")

# --- 服务依赖注入 ---
def get_task_service():
    # 假设 TaskService 可以在没有参数的情况下初始化，
    # 或者其依赖项 (如 Celery 应用) 是全局可用/配置的。
    """提供 TaskService 的实例。"""
    return TaskService()

# --- API 端点 ---
@router.get("/{task_id}", response_model=TaskStatusDetailResponse, summary="获取 Celery 任务状态")
async def get_celery_task_status(
    task_id: str = Path(..., description="要查询的 Celery 任务 ID。", min_length=1),
    task_service: TaskService = Depends(get_task_service)
):
    """
    通过任务 ID 检索 Celery 任务的状态、结果和详情。
    """
    if not task_id or task_id.isspace():
        # 路径验证应该会捕获此问题，但作为安全措施。
        # 任务 ID 不能为空。
        raise HTTPException(status_code=400, detail="任务 ID 不能为空。")
        
    try:
        # TaskService.get_task_status 返回一个字典:
        # {"task_id": str, "status": str, "result": Any, "details": Any}
        status_info = task_service.get_task_status(task_id=task_id)
        
        # 如果 Celery 连接失败或服务内部发生其他问题，
        # TaskService 可能会返回 "UNKNOWN" 或 "ERROR_FETCHING_STATUS" 之类的状态。
        # 这些是返回给客户端的有效状态。
        if status_info.get("status") == "UNKNOWN" and "Celery connection error" in str(status_info.get("result")):
             # 如果 Celery 关闭，可能映射到 503 Service Unavailable
             pass # 目前，按服务返回原样。

        return TaskStatusDetailResponse(**status_info)
        
    except Exception as e:
        # 这将捕获此端点处理程序本身的意外错误，
        # 而不是 TaskService 内部已处理并返回的错误。
        # 获取任务状态时发生意外错误
        raise HTTPException(status_code=500, detail=f"获取任务状态时发生意外错误: {str(e)}")