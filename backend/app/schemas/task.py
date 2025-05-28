from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class TaskBase(BaseModel):
    """任务的基础模型。"""
    id: str = Field(..., description="任务的唯一 ID (通常是 Celery 任务 ID)。")
    task_type: str = Field(..., description="任务的类型 (例如：'index', 'wiki_generation')。")
    status: str = Field(..., description="任务的当前状态 (例如：'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')。")
    
class TaskStatusResponse(TaskBase):
    """任务状态查询的响应模型 (可能已简化)。"""
    # 此模型可能被返回更 summarised 任务状态的端点使用。
    # /api/status/{task_id} 端点使用在 status.py 中定义的 TaskStatusDetailResponse，
    # 它与 TaskService.get_task_status 的输出更一致。
    # 如果系统的其他部分使用此 TaskStatusResponse，则可以保留它，
    # 或者如果全局首选 TaskStatusDetailResponse，则可以弃用/删除它。
    progress: int = Field(0, description="任务进度百分比 (0-100)。")
    message: Optional[str] = Field(None, description="与任务当前状态或结果相关的消息。")
    result_url: Optional[str] = Field(None, description="用于检索任务结果的 URL (如果适用)。")
    
    class Config:
        orm_mode = True
        
class TaskDetail(TaskBase):
    """任务的详细信息，通常对应于数据库模型。"""
    # 此模型似乎与数据库 `Task` 模型更一致。
    repository_id: Optional[str] = Field(None, description="与任务关联的仓库 ID (如果有)。")
    # celery_task_id: Optional[str] = Field(None, description="Celery 的内部任务 ID，如果与主 'id' 不同。") 
    # -> 数据库中的 Task.id 现在是 Celery 任务 ID，因此该字段是多余的。
    progress: int = Field(0, description="任务进度百分比。")
    message: Optional[str] = Field(None, description="状态消息。")
    result: Optional[Dict[str, Any]] = Field(None, description="任务的结果，或失败时的错误详细信息 (JSON 格式)。")
    created_at: datetime = Field(..., description="任务记录创建时的时间戳。")
    updated_at: datetime = Field(..., description="任务记录上次更新时的时间戳。")
    
    class Config:
        orm_mode = True