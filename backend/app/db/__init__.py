# For easier access to database components, import them here.

# Import the Base for Alembic and other ORM operations
from .session import Base

# Import all models to make them accessible via app.db.<ModelName>
# and to ensure they are registered with SQLAlchemy's metadata.
from .models import Repository
from .models import WikiDocument
from .models import Task
from .models import KnowledgeBase # Even if not directly modified, it's part of the models

# You can also define an __all__ variable if you want to control `from app.db import *`
__all__ = [
    "Base",
    "Repository",
    "WikiDocument",
    "Task",
    "KnowledgeBase",
]