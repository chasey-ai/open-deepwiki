from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func # 用于服务器端默认时间戳
from sqlalchemy.orm import relationship

# 从 .session 导入 Base，它现在在那里定义
from .session import Base

class Repository(Base):
    """GitHub仓库信息""" # Docstring already in Chinese
    __tablename__ = "repositories"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    url = Column(String(2048), unique=True, index=True, nullable=False) # URL 可能很长
    name = Column(String(255), nullable=False)
    owner = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    last_indexed_at = Column(DateTime, nullable=True) # 上次成功索引的时间戳
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    # 与 WikiDocument 的一对一关系 (一个仓库有一个当前的 wiki 文档)
    wiki_document = relationship("WikiDocument", back_populates="repository", uselist=False, cascade="all, delete-orphan")
    # 与 Task 的一对多关系 (一个仓库可以有多个任务)
    tasks = relationship("Task", back_populates="repository", cascade="all, delete-orphan")
    
    # 与 KnowledgeBase 的关系 (如果保留)
    knowledge_base = relationship("KnowledgeBase", back_populates="repository", uselist=False, cascade="all, delete-orphan")


class WikiDocument(Base):
    """仓库生成的 Wiki 内容"""
    __tablename__ = "wiki_documents"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    content_markdown = Column(Text, nullable=False)  # 生成的 Markdown 格式 Wiki 内容
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    version = Column(Integer, default=1, nullable=False) # 可选：用于 Wiki 内容的版本控制
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 返回 Repository 的关系
    repository = relationship("Repository", back_populates="wiki_document")


class Task(Base):
    """关于异步 Celery 任务的信息"""
    __tablename__ = "tasks"
    
    id = Column(String(255), primary_key=True, index=True)  # Celery 任务 ID
    # repository_id 是 Integer 类型，因为 Repository.id 是 Integer 类型
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=True, index=True) 
    task_name = Column(String(255), nullable=False, index=True)  # 例如：'index_repository', 'generate_wiki'
    status = Column(String(50), nullable=False, index=True)  # 例如：PENDING, STARTED, SUCCESS, FAILURE
    progress = Column(Integer, nullable=True)  # 可选：完成百分比
    result = Column(JSON, nullable=True)  # 存储任务结果或错误信息。使用通用 JSON。
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 返回 Repository 的关系
    repository = relationship("Repository", back_populates="tasks")


# KnowledgeBase 模型存在于原始文件中。
# 本子任务没有明确要求修改它，
# 但如果 Repository.id 类型更改，其到 repositories.id 的外键需要兼容。
# 如果 Repository.id 现在是 Integer，KnowledgeBase.repository_id 也必须是 Integer。
# 并且 KnowledgeBase.id 作为主键也最好是 Integer。
class KnowledgeBase(Base):
    """知识库信息 (可能用于向量存储元数据)"""
    __tablename__ = "knowledge_bases" # 如果数据存在，则保留表名
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True) # 已更改为 Integer 主键
    # repository_id 应与 Repository.id 类型匹配
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, unique=True, index=True) 
    vector_store_path = Column(String(1024), nullable=True)  # 向量存储的路径或标识符
    document_count = Column(Integer, default=0)
    # 添加其他相关字段，例如：embedding_model_name, last_updated_by_task_id
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    repository = relationship("Repository", back_populates="knowledge_base")