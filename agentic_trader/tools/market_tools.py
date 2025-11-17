"""市场数据工具函数（供AI代理调用）"""

import logging
from typing import Dict, Any
from agents.tool import function_tool

logger = logging.getLogger(__name__)

# 全局服务实例（由main.py设置）
_market_data_service = None


def set_market_data_service(service):
    """设置全局市场数据服务实例"""
    global _market_data_service
    _market_data_service = service


@function_tool
def get_all_market_data() -> Dict[str, Any]:
    """
    批量获取所有股票的市场数据（并行）

    Returns:
        包含所有股票数据的字典
    """
    if _market_data_service is None:
        return {"error": "Market data service not initialized"}

    return _market_data_service.fetch_all_market_data()


@function_tool
def get_market_quotes(symbol: str) -> Dict[str, Any]:
    """
    获取单个股票的报价数据

    Args:
        symbol: 股票代码

    Returns:
        报价数据
    """
    if _market_data_service is None:
        return {"error": "Market data service not initialized"}

    try:
        return _market_data_service.fetch_quotes(symbol)
    except Exception as e:
        logger.error(f"Error getting quotes for {symbol}: {e}")
        return {"error": str(e)}


@function_tool
def get_market_depth(symbol: str) -> Dict[str, Any]:
    """
    获取单个股票的市场深度

    Args:
        symbol: 股票代码

    Returns:
        市场深度数据
    """
    if _market_data_service is None:
        return {"error": "Market data service not initialized"}

    try:
        return _market_data_service.fetch_depth(symbol)
    except Exception as e:
        logger.error(f"Error getting depth for {symbol}: {e}")
        return {"error": str(e)}


@function_tool
def get_account_snapshot() -> Dict[str, Any]:
    """
    获取账户资金信息

    Returns:
        账户资金数据
    """
    if _market_data_service is None:
        return {"error": "Market data service not initialized"}

    return _market_data_service.get_account_funds()


@function_tool
def get_current_positions() -> Dict[str, Any]:
    """
    获取当前持仓

    Returns:
        持仓数据
    """
    if _market_data_service is None:
        return {"error": "Market data service not initialized"}

    return _market_data_service.get_positions()
