"""Pytest配置和fixtures"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
import pytz

from agentic_trader.core import TradeState
from agentic_trader.config import Settings


@pytest.fixture
def mock_openalgo_client():
    """Mock OpenAlgo客户端"""
    client = Mock()

    # Mock quotes响应
    client.quotes.return_value = {
        "status": "success",
        "data": {
            "ltp": 1350.50,
            "open": 1340.00,
            "high": 1360.00,
            "low": 1335.00,
            "volume": 1000000,
            "prev_close": 1345.00
        }
    }

    # Mock depth响应
    client.depth.return_value = {
        "status": "success",
        "data": {
            "bids": [{"price": 1350.00, "quantity": 100}],
            "asks": [{"price": 1351.00, "quantity": 50}]
        }
    }

    # Mock positionbook响应
    client.positionbook.return_value = {
        "status": "success",
        "data": []
    }

    # Mock funds响应
    client.funds.return_value = {
        "status": "success",
        "data": {
            "availablecash": 100000.0,
            "m2munrealized": 0.0,
            "m2mrealized": 0.0
        }
    }

    return client


@pytest.fixture
def trade_state():
    """创建TradeState实例"""
    return TradeState()


@pytest.fixture
def test_config():
    """测试配置"""
    return {
        "symbols": ["ICICIBANK", "RELIANCE"],
        "max_investment_per_trade": 10000.0,
        "daily_stop_loss": -10000.0,
        "max_trades_per_symbol": 5,
        "exchange": "NSE",
        "product": "MIS"
    }


@pytest.fixture
def ist_timezone():
    """IST时区"""
    return pytz.timezone('Asia/Kolkata')


@pytest.fixture
def sample_market_data():
    """示例市场数据"""
    return {
        "ICICIBANK": {
            "symbol": "ICICIBANK",
            "ltp": 1350.50,
            "volume": 1000000,
            "bid_ask_ratio": 2.0,
            "rsi": 55.0,
            "macd_trend": "bullish",
            "ema_trend": "bullish"
        },
        "RELIANCE": {
            "symbol": "RELIANCE",
            "ltp": 2450.75,
            "volume": 2000000,
            "bid_ask_ratio": 1.5,
            "rsi": 65.0,
            "macd_trend": "bearish",
            "ema_trend": "neutral"
        }
    }
