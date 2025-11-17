"""订单工具函数（供AI代理调用）"""

import logging
import json
from typing import Dict, Any
from agents.tool import function_tool

logger = logging.getLogger(__name__)

# 全局服务实例（由main.py设置）
_order_executor = None


def set_order_executor(executor):
    """设置全局订单执行器实例"""
    global _order_executor
    _order_executor = executor


@function_tool
def place_market_order(symbol: str, action: str, quantity: int, reason: str) -> Dict[str, Any]:
    """
    下市价单

    Args:
        symbol: 股票代码
        action: 交易动作（BUY/SELL）
        quantity: 数量
        reason: 交易原因

    Returns:
        订单结果
    """
    if _order_executor is None:
        return {"success": False, "error": "Order executor not initialized"}

    return _order_executor.place_market_order(symbol, action, quantity, reason)


@function_tool
def place_bulk_orders(orders: str) -> Dict[str, Any]:
    """
    批量下单

    Args:
        orders: JSON字符串 [{"symbol": "ICICIBANK", "action": "BUY", "quantity": 7, "reason": "..."}, ...]

    Returns:
        批量下单结果
    """
    if _order_executor is None:
        return {"success": False, "error": "Order executor not initialized"}

    try:
        orders_list = json.loads(orders)

        if not isinstance(orders_list, list):
            return {"success": False, "error": "orders must be a JSON array"}

        return _order_executor.place_bulk_orders(orders_list)

    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@function_tool
def square_off_all_positions() -> Dict[str, Any]:
    """
    平仓所有持仓

    Returns:
        平仓结果
    """
    if _order_executor is None:
        return {"success": False, "error": "Order executor not initialized"}

    return _order_executor.square_off_all_positions()


@function_tool
def cancel_all_pending_orders() -> Dict[str, Any]:
    """
    取消所有挂单

    Returns:
        取消结果
    """
    if _order_executor is None:
        return {"success": False, "error": "Order executor not initialized"}

    return _order_executor.cancel_all_pending_orders()
