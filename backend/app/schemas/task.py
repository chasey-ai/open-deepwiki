from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class TaskBase(BaseModel):
    """任务基础模型"""
    id: str
    task_type: str  # 'index', 'wiki', 'query'
    status: str  # 'pending', 'processing', 'completed', 'failed'
    
class TaskStatusResponse(TaskBase):
    """任务状态响应"""
    progress: int = 0
    message: Optional[str] = None
    result_url: Optional[str] = None
    
    class Config:
        orm_mode = True
        
class TaskDetail(TaskBase):
    """任务详细信息"""
    repository_id: Optional[str] = None
    celery_task_id: Optional[str] = None
    progress: int = 0
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True