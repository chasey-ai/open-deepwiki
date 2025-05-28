from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from datetime import datetime

class RepositoryRequest(BaseModel):
    """提供 GitHub 仓库 URL 的请求模型。"""
    url: HttpUrl = Field(..., description="GitHub 仓库的 URL。")
    
class RepositoryBaseInfo(BaseModel):
    """仓库信息的基础模型。"""
    id: str = Field(..., description="仓库的唯一标识符 (例如：'owner_name')。")
    url: str = Field(..., description="仓库的 URL。")
    name: str = Field(..., description="仓库的名称。")
    owner: str = Field(..., description="仓库的所有者。")
    description: Optional[str] = Field(None, description="仓库的描述。")
    
class RepositoryResponse(RepositoryBaseInfo):
    """仓库处理任务的响应模型。"""
    task_id: str = Field(..., description="为仓库处理启动的任务 ID。")
    status: str = Field(..., description="任务的当前状态。")
    message: str = Field(..., description="与任务状态相关的消息。")
    
    class Config:
        orm_mode = True

class RepositoryDetail(RepositoryBaseInfo):
    """包含时间戳的详细仓库信息。"""
    created_at: datetime = Field(..., description="仓库记录创建时的时间戳。")
    updated_at: datetime = Field(..., description="仓库记录上次更新时的时间戳。")
    
    class Config:
        orm_mode = True