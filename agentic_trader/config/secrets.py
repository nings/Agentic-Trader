"""安全的密钥管理"""

import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SecretManager:
    """安全的密钥管理器"""

    def __init__(self):
        """初始化密钥管理器"""
        pass

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        获取密钥（优先级：环境变量 > 默认值）

        Args:
            key: 密钥名称
            default: 默认值

        Returns:
            密钥值或默认值
        """
        # 从环境变量读取
        value = os.getenv(key)
        if value:
            # 验证密钥格式
            if self._validate_key_format(key, value):
                return value
            else:
                logger.warning(f"Invalid format for {key}")
                return default

        # 返回默认值
        return default

    def _validate_key_format(self, key: str, value: str) -> bool:
        """
        验证密钥格式

        Args:
            key: 密钥名称
            value: 密钥值

        Returns:
            是否有效
        """
        validators = {
            "OPENAI_API_KEY": lambda v: v.startswith("sk-"),
            "CEREBRAS_API_KEY": lambda v: v.startswith("csk-"),
            "GROQ_API_KEY": lambda v: v.startswith("gsk-"),
        }

        validator = validators.get(key)
        if validator:
            return validator(value)
        return True

    def set_secret(self, key: str, value: str) -> None:
        """
        设置密钥（仅用于测试）

        Args:
            key: 密钥名称
            value: 密钥值
        """
        os.environ[key] = value


# 全局密钥管理器
secrets = SecretManager()
