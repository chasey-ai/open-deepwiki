from pydantic import BaseModel, Field
from typing import List, Optional

class QueryRequest(BaseModel):
    """用户问题查询请求"""
    repository_id: str = Field(..., description="仓库ID")
    query: str = Field(..., description="用户问题")
    
class SourceDocument(BaseModel):
    """答案来源文档"""
    text: str
    file: Optional[str] = None
    url: Optional[str] = None
    
class QueryResponse(BaseModel):
    """查询结果响应"""
    answer: str
    sources: List[SourceDocument]
    
    class Config:
        orm_mode = True 