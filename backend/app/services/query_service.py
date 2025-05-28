import logging
from fastapi import HTTPException
from typing import Dict, Any, Optional, List

# 确保 agents.pipelines.query_pipeline 可访问。
# 如果项目结构需要，调整导入路径。
from agents.pipelines.query_pipeline import QueryPipeline
from haystack.document_stores import BaseDocumentStore # 用于类型提示
from haystack.schema import Document # 用于类型提示，表示检索到的文档

# 配置日志
logger = logging.getLogger(__name__)
# 应用级别的日志配置应在其他地方完成 (例如，主应用设置)
# 例如: logging.basicConfig(level=logging.INFO)

class QueryService:
    def __init__(self, document_store: Optional[BaseDocumentStore] = None):
        """
        初始化 QueryService。
        QueryPipeline 在此处实例化。如果 pipeline 在初始化时需要 document_store
        (例如，为 retriever 配置)，则应在此处传递。

        参数:
            document_store: 一个可选的 Haystack DocumentStore 实例。
                            `agents.pipelines.query_pipeline.py` 中的 QueryPipeline
                            被设计为接受此参数。
        """
        try:
            self.query_pipeline = QueryPipeline(document_store=document_store)
            logger.info("QueryService: QueryPipeline 初始化成功。") # QueryService: QueryPipeline initialized successfully.
        except Exception as e:
            logger.exception("QueryService: QueryPipeline 初始化期间发生严重错误。") # QueryService: Critical error during QueryPipeline initialization.
            # 这是一个严重故障；服务无法运行。
            # QueryService: QueryPipeline 初始化失败
            raise RuntimeError(f"QueryService: QueryPipeline 初始化失败: {str(e)}")

    def answer_question(self, repo_url: str, question: str) -> Dict[str, Any]:
        """
        回答用户提出的与特定仓库 URL 相关的问题。
        repo_url 用于在文档存储中筛选文档。

        参数:
            repo_url: GitHub 仓库的 URL，用于筛选相关文档。
            question: 用户提出的问题。

        返回:
            一个包含问题、仓库 URL、答案和源文档的字典。
            示例:
            {
                "query": "X 是什么?",
                "repo_url": "https://github.com/user/repo",
                "answer": "X 是一个用于...的框架",
                "documents": [
                    {"content": "...", "meta": {"file_path": "README.md", ...}}, ...
                ]
            }

        引发:
            HTTPException: 如果输入无效或查询过程中发生错误。
        """
        if not question or question.strip() == "":
            logger.warning(f"QueryService: 收到针对 repo_url: {repo_url} 的空问题或仅包含空格的问题。") # QueryService: Received an empty or whitespace-only question for repo_url: {repo_url}.
            # 问题不能为空。
            raise HTTPException(status_code=400, detail="问题不能为空。")
        
        if not repo_url or repo_url.strip() == "": # 同时验证 repo_url
            logger.warning(f"QueryService: 收到针对问题: {question} 的空仓库 URL 或仅包含空格的仓库 URL。") # QueryService: Received an empty or whitespace-only repo_url for question: {question}.
            # 仓库 URL 不能为空。
            raise HTTPException(status_code=400, detail="仓库 URL 不能为空。")

        logger.info(f"QueryService: 正在处理针对 repo_url '{repo_url}' 的问题: '{question}'") # QueryService: Processing question for repo_url '{repo_url}': '{question}'

        try:
            # 准备 QueryPipeline 的输入。
            # pipeline 的 `run` 方法需要 `query` 和 `filters`。
            # `filters` 字典应指定 `repo_url` 以限定搜索范围。
            # 这假设 DocumentStore 中的文档在其元数据中包含 `repo_url`。
            pipeline_params = {
                "query": question,
                "filters": {"repo_url": repo_url} 
                # 如果 pipeline.run 需要且此处期望，则添加其他可选参数，如 top_k
                # "top_k_retriever": 5, # 示例
            }
            
            logger.debug(f"QueryService: 使用参数调用 QueryPipeline: {pipeline_params}") # QueryService: Invoking QueryPipeline with parameters: {pipeline_params}
            # pipeline.run() 的 `data` 参数通常在 pipeline 中的第一个组件
            # 需要 'query' 或 'filters' 之外的特定命名输入时使用。
            # query_pipeline.py 的 run 方法直接将 query, filters 等作为参数。
            # 所以，我们解包 pipeline_params。
            pipeline_output = self.query_pipeline.run(**pipeline_params)
            logger.debug(f"QueryService: 从 QueryPipeline 收到输出: {pipeline_output}") # QueryService: Received output from QueryPipeline: {pipeline_output}

            if not pipeline_output:
                logger.error(f"QueryService: QueryPipeline 返回了空或 None 的输出。仓库: '{repo_url}', 问题: '{question}'。") # QueryService: QueryPipeline returned empty or None output. Repo: '{repo_url}', Question: '{question}'.
                # 查询 pipeline 未返回任何输出。
                raise HTTPException(status_code=500, detail="查询 pipeline 未返回任何输出。")

            # 根据 QueryPipeline 的已知输出结构提取答案和文档。
            # 来自 `agents/pipelines/query_pipeline.py`:
            # - LLM 的回复: `pipeline_output['llm']['replies'][0]`
            # - 检索到的文档: `pipeline_output['retriever']['documents']`
            
            llm_output = pipeline_output.get("llm", {})
            answer_list = llm_output.get("replies", [])
            answer = answer_list[0].strip() if answer_list and isinstance(answer_list[0], str) else None

            retriever_output = pipeline_output.get("retriever", {})
            source_documents = retriever_output.get("documents", [])
            
            # 将 Haystack Document 对象转换为更适合 API 的字典格式
            # 这使得服务的响应可序列化，并将其与 Haystack 内部的 Document 类解耦。
            formatted_documents = []
            for doc in source_documents:
                if isinstance(doc, Document):
                    formatted_doc = {
                        "content": doc.content,
                        "meta": doc.meta,
                        # "id": doc.id, # 可选，如果前端需要
                        # "score": doc.score # 可选，如果 retriever 提供分数且有用
                    }
                    formatted_documents.append(formatted_doc)
                else:
                    logger.warning(f"QueryService: 在 retriever 输出中遇到非 Document 对象: {type(doc)}") # QueryService: Encountered non-Document object in retriever output: {type(doc)}


            if answer is None:
                # 如果 LLM 未提供答案，则说明这一点可能是合适的。
                # 如果没有答案意味着“未找到”，这也可以是 404。
                logger.info(f"QueryService: LLM 未找到直接答案。仓库: '{repo_url}', 问题: '{question}'。") # QueryService: No direct answer found by LLM. Repo: '{repo_url}', Question: '{question}'.
                # 未能找到您问题的直接答案。但是，检索到了相关文档。
                answer = "未能找到您问题的直接答案。但是，检索到了相关文档。"
                if not formatted_documents:
                     # 对不起，根据可用信息，我找不到您问题的答案或任何相关文档。
                     answer = "对不起，根据可用信息，我找不到您问题的答案或任何相关文档。"


            logger.info(f"QueryService: 成功处理问题。仓库: '{repo_url}'。已生成答案: {bool(answer and 'Sorry' not in answer and '对不起' not in answer)}") # QueryService: Successfully processed question. Repo: '{repo_url}'. Answer generated: {bool(answer and 'Sorry' not in answer)}
            
            return {
                "query": question,
                "repo_url": repo_url,
                "answer": answer,
                "documents": formatted_documents 
            }
            
        except HTTPException: # 如果是我们抛出的 HTTPException，则重新引发
            raise
        except Exception as e:
            logger.exception(f"QueryService: 查询处理期间发生意外错误。仓库: '{repo_url}', 问题: '{question}'。") # QueryService: An unexpected error occurred during query processing. Repo: '{repo_url}', Question: '{question}'.
            # 除非需要，否则避免向客户端泄漏内部错误详细信息。
            # 处理您的问题时发生错误
            raise HTTPException(status_code=500, detail=f"处理您的问题时发生错误: {str(e)}")

# QueryService 如何实例化和使用的示例 (例如，在 FastAPI 应用中):
#
# from haystack.document_stores import InMemoryDocumentStore
# from backend.app.services.query_service import QueryService
#
# # 全局或应用范围的文档存储
# global_document_store = InMemoryDocumentStore(use_bm25=True)
# # ... (用文档填充 global_document_store) ...
# # 示例:
# # from haystack.schema import Document
# # docs_to_index = [
# #    Document(content="LangChain is a framework.", meta={"repo_url": "https://github.com/langchain-ai/langchain"}),
# #    Document(content="Haystack helps build LLM apps.", meta={"repo_url": "https://github.com/deepset-ai/haystack"})
# # ]
# # global_document_store.write_documents(docs_to_index)
#
# # 在 FastAPI 路由中:
# # query_service_instance = QueryService(document_store=global_document_store)
# # result = query_service_instance.answer_question(
# #     repo_url="https://github.com/langchain-ai/langchain",
# #     question="What is LangChain?"
# # )
# # return result