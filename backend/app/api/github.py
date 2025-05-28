from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Response

# 导入当前的服务和schemas
from app.schemas.github import RepositoryRequest, RepositoryResponse
# 假设新的 GithubService 位于 app.services.github_service
# 旧的 GithubService 也可能名为 github_service (可能是一个实例)。
# 为避免混淆，这里明确导入。
from app.services.github_service import GithubService as NewGithubService # 我实现的新服务
from app.services.task_service import TaskService # 我实现的新服务

# 现有代码使用名为 `github_service` 和 `task_service` 的实例。
# 对于新的端点，我将为 NewGithubService 使用依赖注入。
# 如果现有的 /repository 端点需要保留并使用旧服务，
# 我们需要确保它们可用或对其进行重构。
# 目前，我假设现有的 `github_service` 和 `task_service` 实例
# 来自旧的实现，并将它们保留给现有端点。

router = APIRouter()

# 新 GithubService 的依赖项
def get_new_github_service():
    """提供 NewGithubService 的实例。"""
    return NewGithubService()

# 新 TaskService 的依赖项 (如果旧端点需要，应进行更新)
# 目前，假设旧端点使用的是较旧的 TaskService 实例 (如果 `task_service` 是一个实例的话)。
# 如果 `task_service` 是新 TaskService 的实例，那也可以。
# 为清楚起见，假设旧端点需要更新，或者如果服务冲突则移除旧端点。
# 对于此任务，我将专注于添加新的 /readme 端点。
# 我将按原样保留旧的 /repository 端点，假设其依赖项由现有实例满足。
# 如果 `app.services.github_service.github_service` 是旧实例，则现有端点可以正常工作。
# 如果 `app.services.task_service.task_service` 是新实例，则现有端点可能也可以正常工作。

# 这是现有端点，我将保持原样。
# 它似乎使用了 `github_service.validate_repository_url` 和 `extract_repo_info`，
# 这些不是我编写的 NewGithubService 的一部分 (NewGithubService 有 _extract_owner_repo_from_url)。
# 这意味着 `app.services.github_service.github_service` 是一个旧的服务实例。
# 并且 `app.services.task_service.task_service` 也是一个旧的服务实例 (它有 `create_task`)。
# 我的新 TaskService 有 `create_indexing_task` 等方法。
# 这意味着旧的 /repository 端点在不进行重构的情况下与我的新服务不兼容。
# 在“实现API端点”的范围内，我应该专注于使新端点与新服务一起工作。
# 旧的 /repository 端点可能需要单独处理。

# 目前，我假设全局的 `github_service` 和 `task_service` 是旧的实例。
from app.services.github_service import github_service as old_github_service_instance
from app.services.task_service import task_service as old_task_service_instance


@router.post("/repository", response_model=RepositoryResponse, deprecated=True, summary="旧端点，考虑移除或重构")
async def process_repository(
    repo_request: RepositoryRequest,
    background_tasks: BackgroundTasks
):
    """
    接收GitHub仓库URL，开始处理。(旧实现)
    """
    if not old_github_service_instance.validate_repository_url(str(repo_request.url)):
        raise HTTPException(status_code=400, detail="无效的GitHub仓库URL") # Invalid GitHub repository URL
    
    try:
        repo_info = old_github_service_instance.extract_repo_info(str(repo_request.url))
        # 旧的 task_service.create_task("index", repo_info["id"]) 与新的 TaskService 不同。
        task = old_task_service_instance.create_task("index", repo_info["id"])
        
        # 后台任务逻辑 (在原始代码中被注释掉)
        # background_tasks.add_task(...)
        
        return {
            **repo_info,
            "task_id": task["id"],
            "status": task["status"],
            "message": task["message"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # 服务端错误
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}") # Server error

# 使用新 GithubService 获取 README 的新端点
@router.post("/readme", summary="获取仓库 README 内容")
async def get_repository_readme(
    repo_request: RepositoryRequest,
    service: NewGithubService = Depends(get_new_github_service)
):
    """
    接受一个 GitHub 仓库 URL，并返回其 README 内容。
    使用新的 `GithubService` 进行内容获取。
    """
    try:
        readme_content = await service.get_readme_content(str(repo_request.url))
        return Response(content=readme_content, media_type="text/plain")
    except HTTPException as e:
        # 从服务中重新引发 HTTPException
        raise e
    except Exception as e:
        # 捕获任何其他意外错误
        # 发生意外错误
        raise HTTPException(status_code=500, detail=f"发生意外错误: {str(e)}") # An unexpected error occurred

# TODO: 在 schemas/github.py 中定义一个 ReadmeResponse Pydantic 模型以获取更结构化的响应，
# 例如：class ReadmeResponse(BaseModel): content: str; repo_url: HttpUrl;
# 然后在装饰器中使用 `response_model=ReadmeResponse`。
# 目前，返回纯文本。