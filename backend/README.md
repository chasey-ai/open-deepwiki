# Open-DeepWiki Backend

This is the backend service for Open-DeepWiki, built with FastAPI. It provides functionalities to process GitHub repositories, build knowledge bases, generate Wikis, answer questions, and manage asynchronous tasks.

## Core Components & Features

The backend is structured around several key components:

### 1. Services (`app.services`)
Core logic is encapsulated in services:
- **`GithubService`**: Interacts with the GitHub API to fetch repository data, such as README files.
- **`WikiService`**: Orchestrates the generation of Wiki content. It uses `GithubService` to fetch source material (like READMEs) and `WikiPipeline` (from Haystack agents) to process this material into a structured Wiki. (Note: The current implementation in `WikiService` focuses on initiating generation via `TaskService`; actual content generation logic resides in Celery tasks using Haystack pipelines).
- **`QueryService`**: Handles user questions about repositories. It uses a `QueryPipeline` (Haystack) to search the indexed knowledge base and generate answers.
- **`TaskService`**: Manages asynchronous background tasks using Celery. It allows for dispatching tasks (e.g., repository indexing, Wiki generation) and checking their status.

### 2. API Endpoints (`app.api`)
The backend exposes a RESTful API for interaction:
- **GitHub (`/api/github`)**:
    - `POST /readme`: Fetches the README content of a specified GitHub repository.
- **Wiki (`/api/wiki`)**:
    - `POST /generate`: Triggers an asynchronous task to generate a Wiki for a specified repository. Returns a task ID.
- **Query (`/api/query`)**:
    - `POST /ask`: Submits a question about a specific repository and returns an answer based on its indexed knowledge.
- **Status (`/api/status`)**:
    - `GET /{task_id}`: Retrieves the status and result of an asynchronous task.

For detailed API specifications, request/response models, and interactive testing, please refer to the auto-generated API documentation (see section below).

### 3. Database Models (`app.db.models`)
Data is persisted using SQLAlchemy with the following key models:
- **`Repository`**: Stores information about GitHub repositories, including URL, owner, name, description, and when it was last indexed.
- **`WikiDocument`**: Stores the generated Markdown content for a repository's Wiki, along with versioning and generation timestamps.
- **`Task`**: Tracks asynchronous Celery tasks, including their ID, name, status, progress, and results. Linked to a `Repository`.
- **`KnowledgeBase`**: (Auxiliary model) Stores metadata related to the knowledge base of a repository, like vector store paths or document counts.

### 4. Asynchronous Tasks (`backend.tasks`)
Long-running operations are handled by Celery tasks:
- **`index_repository_task`**: Fetches content from a GitHub repository (starting with the README), processes it through an `IndexPipeline` (Haystack), and updates the database (e.g., `Repository.last_indexed_at`, `KnowledgeBase` info).
- **`generate_wiki_task`**: Uses `WikiService` (which in turn uses `GithubService` and `WikiPipeline`) to generate Wiki content from a repository's README and stores it in the `WikiDocument` table.

## Technology Stack

- **FastAPI**: Modern, fast (high-performance) web framework for building APIs.
- **SQLAlchemy**: SQL toolkit and Object-Relational Mapper (ORM).
- **PostgreSQL (or other SQLAlchemy-compatible DB)**: Relational database for storing application data.
- **Celery**: Distributed task queue for handling asynchronous operations.
- **Redis/RabbitMQ (or other Celery-compatible broker)**: Message broker for Celery.
- **Haystack**: Framework for building applications with LLMs, used here for indexing (ETL), knowledge base querying, and potentially Wiki content generation.
- **Vector Database (e.g., FAISS, Weaviate, Pinecone)**: Used by Haystack for efficient similarity search in knowledge bases (specific choice configured within Haystack pipelines).

## Development Setup

1.  **Create a Virtual Environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Variables**:
    Create a `.env` file in the `backend` directory. Copy `backend/.env.example` (if it exists) or create it with the following essential variables:
    ```dotenv
    # Database connection string (e.g., PostgreSQL)
    DATABASE_URL="postgresql://user:password@host:port/dbname"

    # GitHub Personal Access Token (for higher API rate limits and accessing private repos if needed)
    # Ensure it has 'repo' scope if you intend to access private repositories.
    GITHUB_API_TOKEN="your_github_personal_access_token"

    # Celery configuration
    CELERY_BROKER_URL="redis://localhost:6379/0"  # Example using Redis
    CELERY_RESULT_BACKEND="redis://localhost:6379/0" # Example using Redis
    
    # Path for vector database storage (if applicable, depends on Haystack pipeline config)
    # VECTOR_DB_PATH="./vector_stores" 
    
    # LLM API Keys (if Haystack pipelines use models like OpenAI, Cohere, etc.)
    # OPENAI_API_KEY="your_openai_api_key"
    # COHERE_API_KEY="your_cohere_api_key"
    ```
    Adjust these values based on your local setup and the services you use.

4.  **Database Migrations (if using Alembic)**:
    If Alembic is configured for database migrations (recommended for production and evolving schemas):
    ```bash
    # alembic upgrade head 
    ```
    (Note: Alembic setup is not explicitly part of the current file structure but is a standard practice.)
    For initial setup without Alembic, ensure your database schema matches the models in `app.db.models.py`. You might need to create tables manually or use `Base.metadata.create_all(bind=engine)` from `app.db.session` for development (less suitable for production).

## Running the Backend Service

1.  **FastAPI Application**:
    For development with auto-reload:
    ```bash
    uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
    ```
    For production (adjust workers, host, port as needed):
    ```bash
    uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
    ```

2.  **Celery Worker(s)**:
    In a separate terminal, navigate to the project root (where `backend` directory is) and run:
    ```bash
    celery -A backend.celery_worker.celery_app worker -l info -P eventlet # or -P gevent for async tasks, or default prefork
    ```
    Ensure your Celery broker (e.g., Redis) is running. The `-P eventlet` or `-P gevent` pool might be necessary if your tasks perform many I/O-bound operations or if you are using `async def` tasks natively with Celery (requires specific Celery versions and configurations). For tasks using `asyncio.run()`, the default prefork pool might also work but can be less efficient for async operations.

## Running Unit Tests

To run the unit tests for the backend services and API endpoints:
1. Navigate to the `backend` directory.
2. Ensure all test dependencies are installed (usually part of `requirements.txt` or a separate `requirements-dev.txt`). Key testing libraries include `pytest`, `pytest-asyncio`, and `httpx` (for `TestClient`).
3. Run pytest:
   ```bash
   pytest
   ```
   Or, from the project root:
   ```bash
   pytest backend/
   ```

## API Documentation

Once the FastAPI service is running, interactive API documentation is automatically available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These interfaces allow you to explore API endpoints, view request/response schemas, and test the API directly from your browser. The clarity of this documentation depends on well-defined Pydantic models and descriptive docstrings in the API endpoint functions.