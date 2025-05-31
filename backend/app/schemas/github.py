from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from datetime import datetime

class RepositoryRequest(BaseModel):
    """接收Github仓库URL的请求模型"""
    url: HttpUrl = Field(..., description="GitHub仓库的URL")
    
class RepositoryBaseInfo(BaseModel):
    """基础仓库信息"""
    id: str
    url: str
    name: str
    owner: str
    description: Optional[str] = None
    
class RepositoryResponse(RepositoryBaseInfo):
    """仓库处理任务的响应模型"""
    task_id: str
    status: str
    message: str
    
    class Config:
        orm_mode = True

class RepositoryDetail(RepositoryBaseInfo):
    """详细的仓库信息（包含创建和更新时间）"""
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True