import secrets
from typing import Optional

# 将来可能扩展为更复杂的认证系统
# 目前仅包含基本的API密钥生成和验证

def generate_api_key() -> str:
    """生成安全的API密钥"""
    return secrets.token_urlsafe(32)

def verify_api_key(api_key: Optional[str], valid_keys: list[str]) -> bool:
    """验证API密钥是否有效"""
    if not api_key:
        return False
    return api_key in valid_keys 