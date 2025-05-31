from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import HttpUrl

# 导入服务和模型
from app.services.github_service import github_service
from app.services.task_service import task_service
from app.schemas.github import RepositoryRequest, RepositoryResponse

router = APIRouter()

@router.post("/repository", response_model=RepositoryResponse)
async def process_repository(
    repo_request: RepositoryRequest,
    background_tasks: BackgroundTasks
):
    """
    接收GitHub仓库URL，开始处理流程

    - 验证URL
    - 创建任务ID
    - 启动后台任务：获取仓库内容并构建知识库
    - 返回任务ID，供前端轮询状态
    """
    # 验证仓库URL
    if not github_service.validate_repository_url(str(repo_request.url)):
        raise HTTPException(status_code=400, detail="无效的GitHub仓库URL")
    
    try:
        # 提取仓库信息
        repo_info = github_service.extract_repo_info(str(repo_request.url))

        # 创建任务
        task = task_service.create_task("index", repo_info["id"])
        
        # 在后台处理仓库
        # 实际项目中，这里应该调用Celery任务
        # background_tasks.add_task(
        #     process_github_repository.delay,
        #     str(repo_request.url),
        #     task["id"]
        # )
        
        # 返回响应
        return {
            **repo_info,
            "task_id": task["id"],
            "status": task["status"],
            "message": task["message"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")