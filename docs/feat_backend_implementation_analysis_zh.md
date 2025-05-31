## **中文版项目报告**

**整体摘要：**
`feat/backend-implementation` 分支已经为 FastAPI 后端搭建了基本结构，包括 API 路由定义、服务层、Agent 工作流占位符以及 Celery 任务管理设置。然而，这些组件中的大部分核心逻辑目前都是模拟的或占位符代码。作为项目功能核心的 Haystack Agent 工作流尚未实现。此外，整个 Next.js 前端应用程序也缺失。

**后端状态：**

*   **已实现功能 (部分/骨架):**
    *   FastAPI 应用程序结构 (`app/main.py`)。
    *   API 端点定义在 `app/api/` 目录下 (`github.py`, `query.py`, `status.py`, `wiki.py`)。
    *   服务层结构在 `app/services/` 目录下。
    *   Agent 工作流文件结构在 `agents/pipelines/` 目录下。
    *   Celery Worker 设置 (`celery_worker.py`) 和任务定义在 `tasks.py` 中 (尽管任务是模拟的)。
    *   基本的 GitHub URL 验证和仓库信息提取 (`github_service.py`)。
    *   部分 API 请求/响应的 Pydantic 模型。

*   **缺失的实现和待办事项：**
    *   **API 端点：**
        *   `github.py`: 取消注释并完整实现用于仓库处理的后台任务启动逻辑 (例如，调用 Celery 任务)。
        *   `query.py`: 将模拟响应替换为调用 `query_service.py` 的实际逻辑，并集成 `QueryRequest`/`QueryResponse` 模型。
        *   `status.py`: 将模拟响应替换为调用 `task_service.py` 以获取真实任务状态的实际逻辑，并集成 `TaskStatusResponse` 模型。
        *   `wiki.py`: 将模拟响应替换为调用 `wiki_service.py` 进行生成和检索的实际逻辑，并集成 `WikiRequest`/`WikiResponse` 模型。
    *   **服务：**
        *   `github_service.py`: 实现实际的 GitHub 内容获取 (超越基本信息)。与 `index_pipeline.py` 或运行它的 Celery task 集成。
        *   `query_service.py`: 通过与 `query_pipeline.py` (Haystack) 集成来实现核心的问答逻辑。需要处理知识库检索。
        *   `wiki_service.py`: 通过与 `wiki_pipeline.py` (Haystack) 集成以及为生成的内容提供数据库持久化，来实现核心的 Wiki 生成和检索逻辑。
        *   `task_service.py`: 实现用于创建、跟踪和更新任务状态的实际数据库交互。需要反映 Celery 任务的真实状态。
    *   **Agent 工作流 (Haystack 实现)：**
        *   `index_pipeline.py`: 实现用于获取仓库内容、文本处理、向量化以及存储到向量数据库 (例如，根据 README 中的描述使用 FAISS) 的 Haystack 工作流。
        *   `query_pipeline.py`: 实现用于问题向量化、向量数据库中的相似性搜索以及答案生成 (可能使用 LLM) 的 Haystack 工作流。
        *   `wiki_pipeline.py`: 实现用于从知识库生成结构化内容 (包括摘要和导航数据创建) 的 Haystack 工作流。
    *   **Celery 任务 (`tasks.py`)：**
        *   `process_github_repository` 任务：将模拟逻辑替换为对已实现的 `index_pipeline.py` 或其组成的 Haystack 组件的实际调用。确保通过 `task_service.py` 进行适当的错误处理和状态更新。
        *   `generate_wiki` 任务：将模拟逻辑替换为对已实现的 `wiki_pipeline.py` 的实际调用。确保通过 `task_service.py` 进行适当的错误处理和状态更新。
    *   **数据库集成：**
        *   在 `app/db/models.py` 中实现/完成用于存储仓库信息、任务状态、生成的 Wiki 内容、用户数据 (如果计划) 等的数据库模型。
        *   确保 `app/db/session.py` 被正确配置并被服务和任务用于所有数据库操作 (任务、Wiki等的CRUD操作)。

**前端状态：**

*   **确认缺失 `frontend/` 目录：** 整个前端应用程序 (根据 `README.md` 的描述，预计位于 `frontend/` 目录并使用 Next.js 构建) 在此分支中不存在。
*   **详细待办事项 (基于 `README.md`)：**
    *   **项目设置：** 在 `frontend/` 目录中初始化一个新的 Next.js 项目。
    *   **核心页面：**
        *   `src/app/page.tsx`: 首页 (可能用于仓库输入)。
        *   `src/app/loading.tsx`: 全局加载状态组件。
        *   `src/app/wait/`: 用于在处理期间显示进度的页面。
        *   `src/app/wiki/`: 用于显示生成的 Wiki 的页面。
        *   `src/app/query/`: 问答界面的页面。
    *   **可复用组件 (`src/components/`)：**
        *   `RepoInput/`: GitHub 仓库 URL 输入组件。
        *   `ExampleRepos/`: 显示示例仓库的组件。
        *   `WikiNavigation/`: Wiki 导航组件 (整体和页内)。
        *   `QueryInterface/`: 问答输入和显示组件。
        *   `ProgressBar/`: 显示任务进度的组件。
    *   **支持性结构：**
        *   `src/lib/`: 工具函数，用于与后端通信的 API 客户端。
        *   `src/types/`: 数据结构的 TypeScript 类型定义。
        *   `src/styles/`: 全局样式。

**优先待办事项列表 (MVP 的高级别)：**

1.  **实现核心后端逻辑 (知识库创建)：**
    *   使用 Haystack 实现 `index_pipeline.py`。
    *   在 `tasks.py` 中实现 `process_github_repository` Celery 任务以使用此工作流。
    *   完整实现 `github_service.py` 以触发此任务。
    *   将 `github.py` 中的 `/repository` API 连接到服务。
    *   实现 `task_service.py` 和 `/status/{task_id}` API 以进行真实状态更新 (最初专注于索引状态)。
    *   基本的数据库集成，用于存储任务状态和仓库信息。
2.  **实现核心后端逻辑 (Wiki 生成和显示 - 基础版)：**
    *   实现 `wiki_pipeline.py` (基础版本，也许开始时只渲染 README)。
    *   实现 `generate_wiki` Celery 任务以使用此工作流。
    *   完整实现 `wiki_service.py` 以触发此任务并检索基本的 Wiki 内容。
    *   连接 `/wiki/generate` 和 `/wiki/{repo_id}` API。
    *   数据库集成，用于存储和检索生成的 Wiki 内容。
3.  **开发基本的前端外壳：**
    *   设置 Next.js。
    *   创建首页 (`RepoInput`) 以向后端提交仓库 URL。
    *   创建一个基本的 Wiki 显示页面，可以显示从后端获取的 Markdown 内容。
    *   使用状态 API 实现进度显示。
4.  **实现核心后端逻辑 (问答)：**
    *   使用 Haystack 实现 `query_pipeline.py`。
    *   完整实现 `query_service.py`。
    *   连接 `/query` API。
5.  **将问答功能集成到前端：**
    *   开发 `QueryInterface` 组件和查询页面。
