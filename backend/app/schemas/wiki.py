from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class WikiRequest(BaseModel):
    """Wiki生成请求模型"""
    repository_id: str = Field(..., description="仓库ID")

class NavigationItem(BaseModel):
    """Wiki导航项目"""
    title: str
    id: str
    children: Optional[List['NavigationItem']] = None

class WikiContent(BaseModel):
    """Wiki内容模型"""
    repository_id: str
    content: str
    navigation: List[NavigationItem]
    generated_at: datetime
    
    class Config:
        orm_mode = True

class WikiResponse(BaseModel):
    """Wiki生成任务的响应模型"""
    task_id: str
    status: str
    message: str
    
    class Config:
        orm_mode = True