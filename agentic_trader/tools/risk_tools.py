"""风险检查工具函数（供AI代理调用）"""

import logging
import json
from typing import Dict, Any
from agents.tool import function_tool

logger = logging.getLogger(__name__)

# 全局服务实例（由main.py设置）
_risk_manager = None


def set_risk_manager(manager):
    """设置全局风险管理器实例"""
    global _risk_manager
    _risk_manager = manager


@function_tool
def check_risk_constraints(symbol: str, action: str) -> Dict[str, Any]:
    """
    检查单个交易是否符合风险规则

    Args:
        symbol: 股票代码
        action: 交易动作（BUY/SELL）

    Returns:
        风险检查结果 {"allowed": bool, "reason": str}
    """
    if _risk_manager is None:
        return {"error": "Risk manager not initialized"}

    return _risk_manager.check_constraints(symbol, action)


@function_tool
def check_all_risk_constraints(trades: str) -> Dict[str, Any]:
    """
    批量检查多个交易的风险

    Args:
        trades: JSON字符串 [{"symbol": "ICICIBANK", "action": "BUY"}, ...]

    Returns:
        批量检查结果
    """
    if _risk_manager is None:
        return {"success": False, "error": "Risk manager not initialized"}

    try:
        trades_list = json.loads(trades)

        if not isinstance(trades_list, list):
            return {"success": False, "error": "trades must be a JSON array"}

        results = _risk_manager.check_multiple_constraints(trades_list)

        allowed_count = sum(1 for r in results if r["allowed"])

        return {
            "success": True,
            "results": results,
            "allowed_count": allowed_count,
            "total_count": len(results)
        }

    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@function_tool
def calculate_position_size(symbol: str, ltp: float, max_investment: float = 10000.0) -> Dict[str, Any]:
    """
    计算仓位大小

    Args:
        symbol: 股票代码
        ltp: 当前价格
        max_investment: 最大投资金额（默认10000）

    Returns:
        仓位计算结果
    """
    if _risk_manager is None:
        return {"error": "Risk manager not initialized", "quantity": 0}

    return _risk_manager.calculate_position_size(symbol, ltp, max_investment)


@function_tool
def calculate_all_position_sizes(positions: str) -> Dict[str, Any]:
    """
    批量计算仓位大小

    Args:
        positions: JSON字符串 [{"symbol": "ICICIBANK", "ltp": 1350.0}, ...]

    Returns:
        批量计算结果
    """
    if _risk_manager is None:
        return {"success": False, "error": "Risk manager not initialized"}

    try:
        positions_list = json.loads(positions)

        if not isinstance(positions_list, list):
            return {"success": False, "error": "positions must be a JSON array"}

        results = _risk_manager.calculate_multiple_positions(positions_list)

        return {
            "success": True,
            "results": results
        }

    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
