from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional

# 注意：新的 /api/query/ask 端点使用在 backend/app/api/query.py 中定义的 AskQueryRequest 和 AskQueryResponse。
# 以下模型 (QueryRequest, QueryResponse, SourceDocument) 是预先存在的模型。
# 应审查其用法；它们可能用于不同的查询机制，或者可能被弃用/重构。

class QueryRequest(BaseModel):
    """
    提交查询的请求模型。
    注意：当前的 /api/query/ask 使用 repo_url。此模型使用 repository_id。
    考虑统一使用 repo_url 或 repository_id。
    """
    repository_id: str = Field(..., description="要查询的仓库 ID。")
    query: str = Field(..., description="用户提出的问题。")
    # repo_url: Optional[HttpUrl] = Field(None, description="备选：仓库的 URL。") # 如果需要合并，则为例

class SourceDocument(BaseModel):
    """
    表示支持答案的源文档。
    注意：/api/query/ask 端点的响应模型 (AskQueryResponse)
    使用 FormattedSourceDocument，该模型具有 'content' 和 'meta' 字段，
    与 Haystack Document 结构一致。此 SourceDocument 模型
    具有 'text'、'file'、'url' 字段。
    """
    text: str = Field(..., description="源文档中的相关文本片段。")
    file: Optional[str] = Field(None, description="源文档的文件名。")
    url: Optional[HttpUrl] = Field(None, description="源文档或文件的 URL。") # 已更改为 HttpUrl 以进行验证
    
class QueryResponse(BaseModel):
    """
    查询的响应模型。
    注意：/api/query/ask 端点的响应模型 (AskQueryResponse)
    包含原始查询和 repo_url，并且其文档结构不同。
    """
    answer: str = Field(..., description="对查询生成的答案。")
    sources: List[SourceDocument] = Field(..., description="支持答案的源文档列表。")
    
    class Config:
        orm_mode = True