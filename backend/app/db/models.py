from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

Base = declarative_base()

class Repository(Base):
    """GitHub仓库信息"""
    __tablename__ = "repositories"
    
    id = Column(String, primary_key=True)  # 使用格式化的仓库ID，如 "owner_name"
    url = Column(String, nullable=False)
    name = Column(String, nullable=False)
    owner = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关系
    wiki = relationship("Wiki", back_populates="repository", uselist=False)
    knowledge_base = relationship("KnowledgeBase", back_populates="repository", uselist=False)
    tasks = relationship("Task", back_populates="repository")

class KnowledgeBase(Base):
    """知识库信息"""
    __tablename__ = "knowledge_bases"
    
    id = Column(String, primary_key=True)
    repository_id = Column(String, ForeignKey("repositories.id"))
    vector_store_path = Column(String, nullable=False)  # 向量存储的路径
    document_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关系
    repository = relationship("Repository", back_populates="knowledge_base")

class Wiki(Base):
    """Wiki信息"""
    __tablename__ = "wikis"
    
    id = Column(String, primary_key=True)
    repository_id = Column(String, ForeignKey("repositories.id"))
    content = Column(Text, nullable=True)  # Markdown内容
    navigation = Column(JSON, nullable=True)  # 导航数据（JSON格式）
    generated_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关系
    repository = relationship("Repository", back_populates="wiki")

class Task(Base):
    """异步任务信息"""
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True)
    repository_id = Column(String, ForeignKey("repositories.id"), nullable=True)
    celery_task_id = Column(String, nullable=True)
    task_type = Column(String, nullable=False)  # 'index', 'wiki', 'query'
    status = Column(String, nullable=False)  # 'pending', 'processing', 'completed', 'failed'
    progress = Column(Integer, default=0)
    message = Column(String, nullable=True)
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关系
    repository = relationship("Repository", back_populates="tasks") 