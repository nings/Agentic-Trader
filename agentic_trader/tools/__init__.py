"""工具函数模块（供AI代理调用）"""

from .market_tools import (
    get_all_market_data,
    get_market_quotes,
    get_market_depth,
    get_account_snapshot,
    get_current_positions,
    set_market_data_service
)

from .risk_tools import (
    check_risk_constraints,
    check_all_risk_constraints,
    calculate_position_size,
    calculate_all_position_sizes,
    set_risk_manager
)

from .order_tools import (
    place_market_order,
    place_bulk_orders,
    square_off_all_positions,
    cancel_all_pending_orders,
    set_order_executor
)

__all__ = [
    # Market tools
    "get_all_market_data",
    "get_market_quotes",
    "get_market_depth",
    "get_account_snapshot",
    "get_current_positions",
    "set_market_data_service",
    # Risk tools
    "check_risk_constraints",
    "check_all_risk_constraints",
    "calculate_position_size",
    "calculate_all_position_sizes",
    "set_risk_manager",
    # Order tools
    "place_market_order",
    "place_bulk_orders",
    "square_off_all_positions",
    "cancel_all_pending_orders",
    "set_order_executor",
]
