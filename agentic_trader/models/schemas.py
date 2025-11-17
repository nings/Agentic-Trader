"""Pydantic数据模型（输入验证）"""

from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
from enum import Enum


class Action(str, Enum):
    """交易动作"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class PositionCalculationRequest(BaseModel):
    """仓位计算请求"""

    symbol: str = Field(..., min_length=1, max_length=20, pattern=r'^[A-Z]+$')
    ltp: float = Field(..., gt=0, description="Last traded price must be positive")
    max_investment: float = Field(10000.0, gt=0, le=1000000)

    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v):
        """验证股票代码"""
        allowed_symbols = ["ICICIBANK", "RELIANCE", "SBIN", "WIPRO", "ITC"]
        if v not in allowed_symbols:
            raise ValueError(f"Symbol {v} not in allowed list: {allowed_symbols}")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "symbol": "ICICIBANK",
                    "ltp": 1350.50,
                    "max_investment": 10000.0
                }
            ]
        }
    }


class PositionCalculationResponse(BaseModel):
    """仓位计算响应"""

    symbol: str
    ltp: float
    quantity: int = Field(..., ge=0)
    actual_investment: float
    max_investment: float
    formula: str
    success: bool


class OrderRequest(BaseModel):
    """订单请求"""

    symbol: str = Field(..., pattern=r'^[A-Z]+$')
    action: Action
    quantity: int = Field(..., gt=0, le=10000)
    reason: str = Field(..., max_length=200)
    price_type: Literal["MARKET", "LIMIT"] = "MARKET"
    price: Optional[float] = Field(None, gt=0)

    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v):
        """验证股票代码"""
        allowed_symbols = ["ICICIBANK", "RELIANCE", "SBIN", "WIPRO", "ITC"]
        if v not in allowed_symbols:
            raise ValueError(f"Symbol {v} not in allowed list")
        return v

    @field_validator('price')
    @classmethod
    def validate_price(cls, v, info):
        """验证价格"""
        if info.data.get('price_type') == 'LIMIT' and not v:
            raise ValueError("Price required for LIMIT orders")
        return v


class RiskCheckRequest(BaseModel):
    """风险检查请求"""

    symbol: str = Field(..., pattern=r'^[A-Z]+$')
    action: Action
    daily_pnl: float
    trade_count: int = Field(..., ge=0)
    max_trades: int = Field(5, gt=0)
    stop_loss_limit: float = Field(-10000.0, lt=0)


class RiskCheckResponse(BaseModel):
    """风险检查响应"""

    allowed: bool
    reason: str
    symbol: str
    action: Action


class MarketDataResponse(BaseModel):
    """市场数据响应"""

    symbol: str
    ltp: float
    volume: int
    bid_ask_ratio: float
    rsi: float = Field(..., ge=0, le=100)
    macd_trend: Literal["bullish", "bearish", "neutral"]
    ema_trend: Literal["bullish", "bearish", "neutral"]
