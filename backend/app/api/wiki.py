from fastapi import APIRouter, HTTPException, BackgroundTasks

# 将来从服务层导入
# from app.services.wiki_service import generate_wiki, get_wiki_content
# from app.schemas.wiki import WikiRequest, WikiResponse

router = APIRouter()

@router.post("/generate")
async def generate_wiki_endpoint(
    # wiki_request: WikiRequest,
    # background_tasks: BackgroundTasks
):
    """
    为指定仓库生成Wiki
    
    - 接收仓库ID或知识库引用
    - 创建Wiki生成任务
    - 返回任务ID，供前端轮询状态
    """
    # 暂时使用简单的模拟实现
    return {
        "task_id": "sample-wiki-task",
        "status": "processing",
        "message": "Wiki generation started"
    }

@router.get("/{repo_id}")
async def get_wiki(repo_id: str):
    """
    获取指定仓库的Wiki内容
    
    - 返回Wiki的Markdown内容和导航数据
    """
    # 暂时使用简单的模拟实现
    return {
        "repo_id": repo_id,
        "content": "# 示例Wiki\n\n这是为仓库生成的Wiki示例内容",
        "navigation": [
            {"title": "简介", "id": "intro"},
            {"title": "使用方法", "id": "usage"}
        ]
    } 