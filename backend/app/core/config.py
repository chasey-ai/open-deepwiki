import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """应用配置设置"""
    # 基础配置
    APP_NAME: str = "Open-DeepWiki"
    API_V1_STR: str = "/api"
    
    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/deepwiki")
    
    # 异步任务配置
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    
    # GitHub API配置
    GITHUB_API_TOKEN: str = os.getenv("GITHUB_API_TOKEN", "")
    
    # 向量数据库存储路径
    VECTOR_DB_PATH: str = os.getenv("VECTOR_DB_PATH", "./data/vector_db")
    
    # 跨域设置
    CORS_ORIGINS: list = ["http://localhost:3000"]  # 前端域名
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# 创建全局设置对象
settings = Settings() 