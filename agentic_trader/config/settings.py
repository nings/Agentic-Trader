"""应用配置管理（使用Pydantic验证）"""

import os
from typing import List, Optional
from enum import Enum
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Environment(str, Enum):
    """环境类型"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class ModelProvider(str, Enum):
    """模型提供商"""
    OPENAI = "openai"
    CEREBRAS = "cerebras"
    GROQ = "groq"
    CUSTOM = "custom"


class Settings(BaseSettings):
    """应用配置（使用Pydantic验证）"""

    # 环境
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = Field(default=False)

    # 模型配置
    model_provider: ModelProvider = ModelProvider.CEREBRAS
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    cerebras_api_key: Optional[str] = None
    cerebras_model: str = "llama3.1-8b"
    groq_api_key: Optional[str] = None
    groq_model: str = "llama-3.3-70b-versatile"
    custom_model: Optional[str] = None
    custom_api_key: Optional[str] = None
    custom_api_base: Optional[str] = None

    # 交易配置
    symbols: List[str] = Field(
        default=["ICICIBANK", "RELIANCE", "SBIN", "WIPRO", "ITC"]
    )
    exchange: str = "NSE"
    product: str = "MIS"
    max_investment_per_trade: float = Field(10000.0, gt=0, le=1000000)
    daily_stop_loss: float = Field(-10000.0, lt=0, ge=-1000000)
    max_trades_per_symbol: int = Field(5, gt=0, le=100)

    # API配置
    openalgo_api_key: str
    openalgo_host: str = "http://127.0.0.1:5000"
    api_timeout: int = Field(30, gt=0, le=300)
    api_retry_attempts: int = Field(3, ge=1, le=10)

    # 调度配置
    trading_interval_minutes: int = Field(5, gt=0, le=60)
    market_open_hour: int = Field(9, ge=0, le=23)
    market_open_minute: int = Field(15, ge=0, le=59)
    square_off_hour: int = Field(15, ge=0, le=23)
    square_off_minute: int = Field(15, ge=0, le=59)
    daily_reset_hour: int = Field(15, ge=0, le=23)
    daily_reset_minute: int = Field(45, ge=0, le=59)

    # 日志配置
    log_level: str = "INFO"
    log_dir: str = "logs"
    enable_structured_logging: bool = True

    # 性能配置
    enable_caching: bool = True
    cache_ttl_seconds: int = Field(5, gt=0, le=3600)
    max_concurrent_requests: int = Field(10, gt=0, le=100)

    @field_validator('openai_api_key')
    @classmethod
    def validate_openai_key(cls, v, info):
        """验证OpenAI密钥"""
        if info.data.get('model_provider') == ModelProvider.OPENAI and not v:
            raise ValueError("OpenAI API key required when using OpenAI provider")
        if v and not v.startswith('sk-'):
            raise ValueError("Invalid OpenAI API key format")
        return v

    @field_validator('cerebras_api_key')
    @classmethod
    def validate_cerebras_key(cls, v, info):
        """验证Cerebras密钥"""
        if info.data.get('model_provider') == ModelProvider.CEREBRAS and not v:
            raise ValueError("Cerebras API key required when using Cerebras provider")
        if v and not v.startswith('csk-'):
            raise ValueError("Invalid Cerebras API key format")
        return v

    @field_validator('groq_api_key')
    @classmethod
    def validate_groq_key(cls, v, info):
        """验证Groq密钥"""
        if info.data.get('model_provider') == ModelProvider.GROQ and not v:
            raise ValueError("Groq API key required when using Groq provider")
        if v and not v.startswith('gsk-'):
            raise ValueError("Invalid Groq API key format")
        return v

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }


class DevelopmentSettings(Settings):
    """开发环境配置"""
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = True
    log_level: str = "DEBUG"
    enable_structured_logging: bool = False


class ProductionSettings(Settings):
    """生产环境配置"""
    environment: Environment = Environment.PRODUCTION
    debug: bool = False
    log_level: str = "WARNING"
    enable_structured_logging: bool = True


def get_settings() -> Settings:
    """获取环境对应的配置"""
    env = os.getenv("ENVIRONMENT", "development").lower()

    if env == "production":
        return ProductionSettings()
    elif env == "staging":
        return Settings(environment=Environment.STAGING)
    else:
        return DevelopmentSettings()


# 全局配置实例
settings = get_settings()
