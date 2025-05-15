# Open-DeepWiki 🚀

输入 GitHub 链接，即刻拥有专属知识库与 Wiki！

## 项目简介

Open-DeepWiki 是一个开源项目，旨在参考优秀的 Deepwiki 产品，实现一个利用 NextJS (前端)、FastAPI (后端) 及 Haystack (AI Agent 工作流) 技术栈构建的替代方案。

本项目的主要目的是学习和探索 AI Agent 及相关技术栈的开发与应用，通过实践来丰富和提升个人在 Agent 开发领域的技术能力。我们致力于通过自动为公开的 GitHub 仓库生成全面的、可交互的知识库和结构化的 Wiki 文档，帮助开发者和学习者以前所未有的便捷性去理解、学习、使用和贡献这些仓库。

还在为理解复杂代码库、查找特定信息或面对缺失/过时的文档而烦恼吗？Open-DeepWiki 为您而来！

## 核心功能 (MVP) ✨

- **自动化知识提取与构建**: 自动从 GitHub 仓库（README、Markdown 文档、代码注释等）获取关键信息，构建可查询的知识库。
- **智能 Wiki 生成**: 基于知识库内容，自动生成一个包含关键信息和导航的基础但实用的 Wiki 页面。
- **上下文感知问答**: 提供自然语言问答界面。系统从知识库中检索信息，生成精准回答。清晰展示答案相关的原文片段（"答案来源"），方便溯源。
- **清晰的状态反馈**: 在处理耗时任务（如知识库构建）时，提供明确的进度反馈。
- **结果复用**: 对于已处理过的仓库，能够缓存结果并允许用户直接访问，节省时间。
- **便捷的交互体验**:
  - 首页提供示例仓库，方便快速体验
  - Wiki 页面支持整体导航和长文内章节导航
  - 支持在 Wiki 页面直接发起提问

## 工作原理简介 ⚙️

Open-DeepWiki 的核心依赖于三个精心设计的 Agent 工作流（基于 Haystack 实现）：

### 知识库构建流程 (Index Workflow)
- **输入**: GitHub 仓库 URL
- **处理**: 获取仓库内容 -> 文本预处理与切分 -> 文本向量化 -> 存入向量数据库
- **输出**: 为该仓库构建的专属向量知识库

### Wiki 文档生成流程 (Wiki Generation Workflow)
- **输入**: 已构建的知识库引用、仓库结构信息
- **处理**: 确定主要内容 (如 README) -> 生成 Wiki 结构与目录 -> （未来：内容摘要）-> 构建导航数据
- **输出**: 结构化的 Wiki 内容（Markdown 格式）和导航数据

### 用户问答流程 (Query Workflow)
- **输入**: 用户自然语言问题、当前仓库标识
- **处理**: 问题向量化 -> 在知识库中检索相关文本块 -> （推荐：使用 LLM 基于上下文生成回答）-> 提取答案来源片段
- **输出**: 生成的回答和相关的上下文原文片段

## 技术栈 🛠️

- **前端**: Next.js (React)
- **后端**: FastAPI (Python)
- **Agent 工作流 & 知识库核心**: Haystack (Python)
- **向量数据库 (MVP)**: FAISS
- **异步任务处理 (推荐)**: Celery + Redis/RabbitMQ
- **数据存储 (任务状态、Wiki内容等)**: PostgreSQL

## 项目文件结构 📂

项目采用分离式架构，文件结构分为三大部分：

### 前端 (Next.js)

```
frontend/
├── public/                 # 静态资源
├── src/
│   ├── app/                # 应用路由与页面
│   │   ├── page.tsx        # 首页
│   │   ├── loading.tsx     # 加载状态组件
│   │   ├── wait/           # 处理等待页面
│   │   ├── wiki/           # Wiki展示页面
│   │   └── query/          # 问答交互页面
│   ├── components/         # 可复用组件
│   │   ├── RepoInput/      # 仓库输入组件
│   │   ├── ExampleRepos/   # 示例仓库展示组件
│   │   ├── WikiNavigation/ # Wiki导航组件
│   │   ├── QueryInterface/ # 问答界面组件
│   │   └── ProgressBar/    # 进度指示器组件
│   ├── lib/                # 工具函数和API封装
│   ├── types/              # TypeScript类型定义
│   └── styles/             # 全局样式
├── package.json
└── next.config.js
```

### 后端 (FastAPI)

```
backend/
├── app/
│   ├── main.py             # FastAPI应用入口
│   ├── api/                # API路由
│   │   ├── github.py       # GitHub相关API
│   │   ├── wiki.py         # Wiki生成与获取API
│   │   ├── query.py        # 问答查询API
│   │   └── status.py       # 任务状态API
│   ├── core/               # 核心配置
│   │   ├── config.py       # 应用配置
│   │   └── security.py     # 安全相关
│   ├── models/             # 数据模型
│   ├── schemas/            # Pydantic模式
│   ├── services/           # 业务服务
│   │   ├── github_service.py   # GitHub内容获取服务
│   │   ├── wiki_service.py     # Wiki生成服务
│   │   └── query_service.py    # 问答服务
│   └── db/                 # 数据库相关
│       ├── session.py      # 数据库会话
│       └── models.py       # 数据库模型
├── celery_worker.py        # Celery工作进程
├── tasks.py                # 异步任务定义
├── requirements.txt
└── Dockerfile
```

### HayStack Agent Pipeline

```
agents/
├── pipelines/
│   ├── index_pipeline.py   # 知识库构建流程
│   ├── wiki_pipeline.py    # Wiki文档生成流程
│   └── query_pipeline.py   # 用户问答流程
├── components/
│   ├── retrievers/         # 自定义检索组件
│   ├── processors/         # 文本处理组件
│   └── generators/         # 内容生成组件
├── utils/
│   ├── text_utils.py       # 文本处理工具
│   ├── vector_utils.py     # 向量操作工具
│   └── markdown_utils.py   # Markdown处理工具
├── config/
│   ├── pipeline_config.py  # 流程配置
│   └── model_config.py     # 模型配置
└── data/
    └── document_store/     # 向量数据库存储位置
```

## 快速开始 (概念) 🚀

1. **访问首页**: 打开 Open-DeepWiki 应用
2. **输入链接或选择示例**:
   - 在输入框粘贴一个公开的 GitHub 仓库链接，点击"开始分析"
   - 或从"示例仓库区"选择一个仓库直接开始
3. **等待处理**: 系统将显示处理进度。对于首次分析的仓库，这可能需要一些时间
4. **浏览 Wiki**: 处理完成后，您将被引导至为该仓库生成的 Wiki 页面。通过左侧导航和页面内导航（若有）浏览内容
5. **开始提问**:
   - 点击 Wiki 页面上的"提问"入口，或使用便捷提问框
   - 在问答页面，用自然语言输入您的问题，系统将给出回答和答案来源

## 未来展望 🔮

我们致力于将 Open-DeepWiki 打造成更强大、更智能的开源项目理解工具，并持续深化在 AI Agent 技术领域的学习与实践。未来计划包括：

- 更智能的 Wiki 生成与组织
- 代码级问答与理解
- 增量更新与版本控制
- 多语言仓库支持
- 个性化与自定义配置
- 协作与分享功能
- 支持私有仓库 (通过 OAuth)

## 贡献 💪

作为学习和探索 AI Agent 技术的一部分，我们非常欢迎各种形式的交流与贡献！无论是代码优化、功能建议、文档改进还是 Bug 反馈，都对 Open-DeepWiki 的成长和开发者的学习至关重要。

请查阅 CONTRIBUTING.md (待创建) 了解更多详情。

## 许可证 📄

本项目采用 MIT 许可证 (待创建)。