# Open-DeepWiki 后端

这是 Open-DeepWiki 的后端服务，使用 FastAPI 构建。它提供了处理 GitHub 仓库、构建知识库、生成 Wiki、回答问题以及管理异步任务的功能。

## 核心组件与功能

后端围绕以下几个关键组件构建：

### 1. 服务 (`app.services`)
核心逻辑封装在服务中：
- **`GithubService`**: 与 GitHub API 交互以获取仓库数据，例如 README 文件。
- **`WikiService`**: 协调 Wiki 内容的生成。它使用 `GithubService` 获取源材料（如 README），并使用 `WikiPipeline` (来自 Haystack agents) 将这些材料处理成结构化的 Wiki。（注意：`WikiService` 中的当前实现侧重于通过 `TaskService` 启动生成；实际内容生成逻辑位于使用 Haystack 管道的 Celery 任务中）。
- **`QueryService`**: 处理用户关于仓库的问题。它使用 `QueryPipeline` (Haystack) 搜索索引的知识库并生成答案。
- **`TaskService`**: 使用 Celery 管理异步后台任务。它允许分派任务（例如，仓库索引、Wiki 生成）并检查其状态。

### 2. API 端点 (`app.api`)
后端公开一个 RESTful API 用于交互：
- **GitHub (`/api/github`)**:
    - `POST /readme`: 获取指定 GitHub 仓库的 README 内容。
- **Wiki (`/api/wiki`)**:
    - `POST /generate`: 触发一个异步任务为指定仓库生成 Wiki。返回一个任务 ID。
- **Query (`/api/query`)**:
    - `POST /ask`: 提交一个关于特定仓库的问题，并根据其索引知识返回答案。
- **Status (`/api/status`)**:
    - `GET /{task_id}`: 检索异步任务的状态和结果。

有关详细的 API 规范、请求/响应模型以及交互式测试，请参阅下面自动生成的 API 文档部分。

### 3. 数据库模型 (`app.db.models`)
数据使用 SQLAlchemy 持久化，包含以下关键模型：
- **`Repository`**: 存储有关 GitHub 仓库的信息，包括 URL、所有者、名称、描述以及上次索引的时间。
- **`WikiDocument`**: 存储为仓库生成的 Markdown 格式的 Wiki 内容，以及版本控制和生成时间戳。
- **`Task`**: 跟踪异步 Celery 任务，包括其 ID、名称、状态、进度和结果。与 `Repository` 关联。
- **`KnowledgeBase`**: (辅助模型) 存储与仓库知识库相关的元数据，如向量存储路径或文档计数。

### 4. 异步任务 (`backend.tasks`)
长时间运行的操作由 Celery 任务处理：
- **`index_repository_task`**: 从 GitHub 仓库获取内容（从 README 开始），通过 `IndexPipeline` (Haystack) 处理，并更新数据库（例如，`Repository.last_indexed_at`，`KnowledgeBase` 信息）。
- **`generate_wiki_task`**: 使用 `WikiService`（它又使用 `GithubService` 和 `WikiPipeline`）从仓库的 README 生成 Wiki 内容，并将其存储在 `WikiDocument` 表中。

## 技术栈

- **FastAPI**: 用于构建 API 的现代化、快速（高性能）Web 框架。
- **SQLAlchemy**: SQL 工具包和对象关系映射器 (ORM)。
- **PostgreSQL (或其他 SQLAlchemy 兼容的数据库)**: 用于存储应用程序数据的关系数据库。
- **Celery**: 用于处理异步操作的分布式任务队列。
- **Redis/RabbitMQ (或其他 Celery 兼容的 broker)**: Celery 的消息代理。
- **Haystack**: 用于构建 LLM 应用程序的框架，此处用于索引 (ETL)、知识库查询以及潜在的 Wiki 内容生成。
- **向量数据库 (例如 FAISS, Weaviate, Pinecone)**: Haystack 用于在知识库中进行高效相似性搜索（具体选择在 Haystack 管道中配置）。

## 开发环境搭建

1.  **创建虚拟环境**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows 系统: venv\Scripts\activate
    ```

2.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **环境变量**:
    在 `backend` 目录中创建一个 `.env` 文件。复制 `backend/.env.example` (如果存在) 或使用以下基本变量创建它：
    ```dotenv
    # 数据库连接字符串 (例如 PostgreSQL)
    DATABASE_URL="postgresql://user:password@host:port/dbname"

    # GitHub 个人访问令牌 (用于更高的 API 速率限制以及在需要时访问私有仓库)
    # 如果您打算访问私有仓库，请确保它具有 'repo' 范围。
    GITHUB_API_TOKEN="your_github_personal_access_token"

    # Celery 配置
    CELERY_BROKER_URL="redis://localhost:6379/0"  # 使用 Redis 的示例
    CELERY_RESULT_BACKEND="redis://localhost:6379/0" # 使用 Redis 的示例
    
    # 向量数据库存储路径 (如果适用，取决于 Haystack 管道配置)
    # VECTOR_DB_PATH="./vector_stores" 
    
    # LLM API 密钥 (如果 Haystack 管道使用像 OpenAI, Cohere 等模型)
    # OPENAI_API_KEY="your_openai_api_key"
    # COHERE_API_KEY="your_cohere_api_key"
    ```
    根据您的本地设置和使用的服务调整这些值。

4.  **数据库迁移 (如果使用 Alembic)**:
    如果 Alembic 配置用于数据库迁移 (建议用于生产和不断变化的模式)：
    ```bash
    # alembic upgrade head 
    ```
    (注意：Alembic 设置并非当前文件结构的明确部分，但它是一种标准做法。)
    对于没有 Alembic 的初始设置，请确保您的数据库模式与 `app.db.models.py` 中的模型匹配。您可能需要手动创建表，或在开发中使用 `app.db.session` 中的 `Base.metadata.create_all(bind=engine)` (不太适合生产环境)。

## 运行后端服务

1.  **FastAPI 应用**:
    用于带自动重载的开发模式：
    ```bash
    uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
    ```
    用于生产环境 (根据需要调整 worker 数量、主机和端口)：
    ```bash
    uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
    ```

2.  **Celery Worker(s)**:
    在单独的终端中，导航到项目根目录 (包含 `backend` 目录的位置) 并运行：
    ```bash
    celery -A backend.celery_worker.celery_app worker -l info -P eventlet # 或使用 -P gevent 处理异步任务，或默认的 prefork
    ```
    确保您的 Celery broker (例如 Redis) 正在运行。如果您的任务执行大量 I/O 密集型操作，或者如果您在 Celery 中本地使用 `async def` 任务 (需要特定的 Celery 版本和配置)，则可能需要 `-P eventlet` 或 `-P gevent` 池。对于使用 `asyncio.run()` 的任务，默认的 prefork 池也可能有效，但对于异步操作效率较低。

## 运行单元测试

要为后端服务和 API 端点运行单元测试：
1. 导航到 `backend` 目录。
2. 确保已安装所有测试依赖项 (通常是 `requirements.txt` 的一部分或单独的 `requirements-dev.txt`)。关键的测试库包括 `pytest`、`pytest-asyncio` 和 `httpx` (用于 `TestClient`)。
3. 运行 pytest:
   ```bash
   pytest
   ```
   或者，从项目根目录运行：
   ```bash
   pytest backend/
   ```

## API 文档

FastAPI 服务运行后，可通过以下地址自动获得交互式 API 文档：
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

这些界面允许您浏览 API 端点、查看请求/响应模式，并直接从浏览器测试 API。此文档的清晰度取决于定义良好的 Pydantic 模型和 API 端点函数中描述性的文档字符串。