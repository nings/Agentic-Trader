"""输入验证工具"""

from typing import List


def validate_symbol(symbol: str, allowed_symbols: List[str]) -> bool:
    """
    验证股票代码

    Args:
        symbol: 股票代码
        allowed_symbols: 允许的股票列表

    Returns:
        是否有效

    Raises:
        ValueError: 如果股票代码无效
    """
    if not symbol:
        raise ValueError("Symbol cannot be empty")

    if not symbol.isupper():
        raise ValueError(f"Symbol must be uppercase: {symbol}")

    if symbol not in allowed_symbols:
        raise ValueError(f"Symbol {symbol} not in allowed list: {allowed_symbols}")

    return True


def validate_quantity(quantity: int, min_qty: int = 1, max_qty: int = 10000) -> bool:
    """
    验证订单数量

    Args:
        quantity: 数量
        min_qty: 最小数量
        max_qty: 最大数量

    Returns:
        是否有效

    Raises:
        ValueError: 如果数量无效
    """
    if not isinstance(quantity, int):
        raise ValueError(f"Quantity must be an integer, got {type(quantity)}")

    if quantity < min_qty:
        raise ValueError(f"Quantity {quantity} below minimum {min_qty}")

    if quantity > max_qty:
        raise ValueError(f"Quantity {quantity} exceeds maximum {max_qty}")

    return True


def validate_price(price: float, min_price: float = 0.01) -> bool:
    """
    验证价格

    Args:
        price: 价格
        min_price: 最小价格

    Returns:
        是否有效

    Raises:
        ValueError: 如果价格无效
    """
    if not isinstance(price, (int, float)):
        raise ValueError(f"Price must be a number, got {type(price)}")

    if price <= 0:
        raise ValueError(f"Price must be positive, got {price}")

    if price < min_price:
        raise ValueError(f"Price {price} below minimum {min_price}")

    return True
