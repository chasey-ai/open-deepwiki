from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func # For server-side default timestamps
from sqlalchemy.orm import relationship

# Import Base from .session where it's now defined
from .session import Base

class Repository(Base):
    """GitHub仓库信息"""
    __tablename__ = "repositories"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    url = Column(String(2048), unique=True, index=True, nullable=False) # URLs can be long
    name = Column(String(255), nullable=False)
    owner = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    last_indexed_at = Column(DateTime, nullable=True) # Timestamp of the last successful indexing
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    # One-to-one relationship with WikiDocument (a repository has one current wiki document)
    wiki_document = relationship("WikiDocument", back_populates="repository", uselist=False, cascade="all, delete-orphan")
    # One-to-many relationship with Task (a repository can have multiple tasks)
    tasks = relationship("Task", back_populates="repository", cascade="all, delete-orphan")
    
    # Relationship to KnowledgeBase (if kept)
    knowledge_base = relationship("KnowledgeBase", back_populates="repository", uselist=False, cascade="all, delete-orphan")


class WikiDocument(Base):
    """Generated Wiki content for a repository"""
    __tablename__ = "wiki_documents"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    content_markdown = Column(Text, nullable=False)  # The generated Wiki content in Markdown
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    version = Column(Integer, default=1, nullable=False) # Optional: for versioning Wiki content
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship back to Repository
    repository = relationship("Repository", back_populates="wiki_document")


class Task(Base):
    """Information about asynchronous Celery tasks"""
    __tablename__ = "tasks"
    
    id = Column(String(255), primary_key=True, index=True)  # Celery Task ID
    # repository_id is Integer because Repository.id is Integer
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=True, index=True) 
    task_name = Column(String(255), nullable=False, index=True)  # e.g., 'index_repository', 'generate_wiki'
    status = Column(String(50), nullable=False, index=True)  # e.g., PENDING, STARTED, SUCCESS, FAILURE
    progress = Column(Integer, nullable=True)  # Optional: percentage completion
    result = Column(JSON, nullable=True)  # Store task result or error information. Using generic JSON.
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship back to Repository
    repository = relationship("Repository", back_populates="tasks")


# The KnowledgeBase model was present in the original file.
# It's not explicitly requested for modification in this subtask,
# but its ForeignKey to repositories.id needs to be compatible if Repository.id type changes.
# If Repository.id is now Integer, KnowledgeBase.repository_id must also be Integer.
# And KnowledgeBase.id might also be better as Integer PK.
class KnowledgeBase(Base):
    """Knowledge_base_information (Potentially for vector store metadata)"""
    __tablename__ = "knowledge_bases" # Keep table name if data exists
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True) # Changed to Integer PK
    # repository_id should match Repository.id type
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, unique=True, index=True) 
    vector_store_path = Column(String(1024), nullable=True)  # Path to vector store or identifier
    document_count = Column(Integer, default=0)
    # Add other relevant fields, e.g., embedding_model_name, last_updated_by_task_id
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    repository = relationship("Repository", back_populates="knowledge_base")