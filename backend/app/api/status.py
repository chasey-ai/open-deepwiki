from fastapi import APIRouter, HTTPException

# 将来从服务层导入
# from app.services.task_service import get_task_status
# from app.schemas.task import TaskStatusResponse

router = APIRouter()

@router.get("/{task_id}")
async def get_status(task_id: str):
    """
    获取任务状态

    - 根据任务ID返回当前状态
    - 如果完成，提供结果链接
    """
    # 暂时使用简单的模拟实现
    return {
        "task_id": task_id,
        "status": "processing",  # 'processing', 'completed', 'failed'
        "progress": 65,  # 百分比
        "message": "正在处理仓库内容...",
        "result_url": None  # 完成时提供结果的URL
    }