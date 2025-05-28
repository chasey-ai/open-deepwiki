from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime

# 注意：/api/wiki/generate 端点使用来自 app.schemas.github 的 RepositoryRequest
# 和在 app.api.wiki 中定义的 TaskCreationResponse。
# 以下模型可能用于其他计划的 Wiki 功能 (例如，直接检索)。

class WikiRequest(BaseModel):
    """Wiki 生成请求模型 (可能用于直接的、非基于任务的生成或特定内容)。"""
    # 当前的 /api/wiki/generate 端点不直接使用此模型，
    # 该端点使用 RepositoryRequest。如果此模型用于其他目的，应阐明其用法。
    repository_url: HttpUrl = Field(..., description="要为其生成/检索 Wiki 的仓库 URL。")
    # repository_id: str = Field(..., description="仓库 ID") # 原始字段，为保持一致性已更改为 URL

class NavigationItem(BaseModel):
    """表示 Wiki 导航结构中的单个项目。"""
    title: str = Field(..., description="导航项目的显示标题。")
    id: str = Field(..., description="此导航项目的唯一标识符 (例如，用于链接)。")
    children: Optional[List['NavigationItem']] = Field(None, description="嵌套的导航项目 (如果有)。")

NavigationItem.update_forward_refs() # 用于自引用的 'children'

class WikiContentResponse(BaseModel):
    """用于传递生成的 Wiki 内容的响应模型。"""
    repository_url: HttpUrl = Field(..., description="此 Wiki 所属仓库的 URL。")
    content_markdown: str = Field(..., description="生成的 Markdown 格式 Wiki 内容。")
    navigation: Optional[List[NavigationItem]] = Field(None, description="Wiki 的导航结构 (如果可用)。")
    generated_at: datetime = Field(..., description="此版本 Wiki 生成时的时间戳。")
    version: int = Field(1, description="此 Wiki 文档的版本号。")
    
    class Config:
        orm_mode = True

# 用于任务创建的 WikiResponse 由 app.api.wiki.py 中的 TaskCreationResponse 处理。
# 此 WikiResponse 可能用于不同上下文或可以弃用。
# class OldWikiTaskResponse(BaseModel):
#     """Wiki 生成任务的响应模型 (可能已弃用)。"""
#     task_id: str = Field(..., description="Wiki 生成任务的 ID。")
#     status: str = Field(..., description="任务的当前状态。")
#     message: str = Field(..., description="与任务状态相关的消息。")
    
#     class Config:
#         orm_mode = True