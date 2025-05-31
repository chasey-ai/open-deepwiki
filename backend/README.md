# Open-DeepWiki 后端

基于 FastAPI 的 Open-DeepWiki 后端服务。

## 功能概述

- 处理 GitHub 仓库 URL 并构建知识库
- 生成和提供 Wiki 内容
- 处理用户查询并提供智能回答
- 监控任务进度和状态

## 技术栈

- FastAPI (Web 框架)
- SQLAlchemy (ORM)
- PostgreSQL (数据库)
- Celery (异步任务)
- Haystack (知识库和问答)
- FAISS (向量数据库)

## 开发准备

1. 创建虚拟环境:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. 安装依赖:
```bash
pip install -r requirements.txt
```

3. 环境变量设置:
创建 `.env` 文件，包含以下内容:
```
DATABASE_URL=postgresql://postgres:postgres@localhost/deepwiki
GITHUB_API_TOKEN=your_github_token
```

## 运行服务

开发模式运行:
```bash
uvicorn app.main:app --reload
```

生产环境运行:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API 文档

启动服务后，访问:

- API 文档: http://localhost:8000/docs
- ReDoc 风格文档: http://localhost:8000/redoc