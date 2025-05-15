from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Open-DeepWiki API",
    description="API for Open-DeepWiki - 输入GitHub链接，即刻拥有专属知识库与Wiki！",
    version="0.1.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境下允许所有来源，生产环境应该更严格
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to Open-DeepWiki API"}

# 导入并包含路由器
from app.api import github, wiki, query, status
app.include_router(github.router, prefix="/api/github", tags=["github"])
app.include_router(wiki.router, prefix="/api/wiki", tags=["wiki"])
app.include_router(query.router, prefix="/api/query", tags=["query"])
app.include_router(status.router, prefix="/api/status", tags=["status"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 