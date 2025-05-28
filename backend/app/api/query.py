from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Dict, Any, Optional

# 导入新的 QueryService
from app.services.query_service import QueryService
# 如果 QueryService 直接需要，则导入 Haystack DocumentStore 用于依赖注入
# from haystack.document_stores import BaseDocumentStore

router = APIRouter()

# --- 此端点的 Pydantic 模型 ---
class AskQueryRequest(BaseModel):
    repo_url: HttpUrl = Field(..., description="用于查询的 GitHub 仓库 URL。")
    question: str = Field(..., min_length=1, description="关于仓库提出的问题。")

class FormattedSourceDocument(BaseModel):
    content: str
    meta: Dict[str, Any] = Field(default_factory=dict)
    # id: Optional[str] = None # 如果需要，取消注释
    # score: Optional[float] = None # 如果需要，取消注释

class AskQueryResponse(BaseModel):
    query: str
    repo_url: HttpUrl
    answer: str
    documents: List[FormattedSourceDocument]

# --- 服务依赖注入 ---
def get_query_service():
    """
    提供 QueryService 的实例。
    如果 QueryService 在初始化时需要 DocumentStore，则会在此处提供。
    示例:
    from backend.app.db.document_store_instance import get_document_store # 假设的
    doc_store = get_document_store()
    return QueryService(document_store=doc_store)
    """
    # 我的 QueryService 实现允许 document_store=None,
    # 假设 QueryPipeline 处理其自身的存储或使用默认存储。
    return QueryService(document_store=None) 

# --- API 端点 ---
@router.post("/ask", response_model=AskQueryResponse, summary="针对仓库提出问题")
async def ask_question_about_repository(
    request: AskQueryRequest,
    query_service: QueryService = Depends(get_query_service)
):
    """
    接受一个 GitHub 仓库 URL 和一个问题，然后基于仓库的索引内容返回答案及源文档。
    """
    try:
        repo_url_str = str(request.repo_url)
        # QueryService 的 answer_question 方法返回一个字典:
        # {"query": str, "repo_url": str, "answer": str, "documents": List[FormattedDocument]}
        # 其中 FormattedDocument 是 {"content": str, "meta": dict}
        result_dict = query_service.answer_question(repo_url=repo_url_str, question=request.question)
        
        # 确保结构与 AskQueryResponse 匹配，特别是 'documents'
        # 服务已经将文档格式化为字典 {content: str, meta: dict}
        return AskQueryResponse(
            query=result_dict["query"],
            repo_url=HttpUrl(result_dict["repo_url"]), # 确保是 HttpUrl 类型
            answer=result_dict["answer"],
            documents=[FormattedSourceDocument(**doc) for doc in result_dict["documents"]]
        )
        
    except HTTPException as e:
        # 转发服务引发的 HTTPException (例如，服务输入无效)
        raise e
    except ValueError as ve: # 捕获 Pydantic 验证错误，例如 HttpUrl 转换失败
        # 无效输入
        raise HTTPException(status_code=400, detail=f"无效输入: {str(ve)}")
    except Exception as e:
        # 捕获处理过程中的任何其他意外错误
        # 处理查询时发生意外错误
        raise HTTPException(status_code=500, detail=f"处理查询时发生意外错误: {str(e)}")

# query.py 中旧的根 POST 端点是一个模拟端点。
# 它已被更具体的 "/ask" 端点替换。