# 为了更方便地访问数据库组件，在此处导入它们。

# 导入 Base 用于 Alembic 和其他 ORM 操作
from .session import Base

# 导入所有模型，使其可以通过 app.db.<ModelName> 访问，
# 并确保它们已在 SQLAlchemy 的元数据中注册。
from .models import Repository
from .models import WikiDocument
from .models import Task
from .models import KnowledgeBase # 即使没有直接修改，它也是模型的一部分。

# 你也可以定义一个 __all__ 变量来控制 `from app.db import *` 的行为
__all__ = [
    "Base",
    "Repository",
    "WikiDocument",
    "Task",
    "KnowledgeBase",
]