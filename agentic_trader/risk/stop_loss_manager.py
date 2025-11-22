"""动态止损管理器"""

import logging
import numpy as np
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class StopLossLevel:
    """止损水平"""
    symbol: str
    entry_price: float
    stop_price: float
    stop_pct: float
    stop_type: str  # 'fixed', 'trailing', 'volatility', 'time'
    last_update: datetime


class DynamicStopLoss:
    """
    动态止损管理器

    根据市场波动率和价格走势动态调整止损位
    """

    def __init__(
        self,
        default_stop_pct: float = 0.02,  # 默认2%止损
        use_atr: bool = True,
        atr_multiplier: float = 2.0
    ):
        """
        初始化动态止损管理器

        Args:
            default_stop_pct: 默认止损百分比
            use_atr: 是否使用ATR调整止损
            atr_multiplier: ATR倍数
        """
        self.default_stop_pct = default_stop_pct
        self.use_atr = use_atr
        self.atr_multiplier = atr_multiplier
        self.stop_levels: Dict[str, StopLossLevel] = {}

    def calculate_stop_loss(
        self,
        symbol: str,
        entry_price: float,
        direction: str,  # 'long' or 'short'
        atr: Optional[float] = None,
        volatility: Optional[float] = None
    ) -> StopLossLevel:
        """
        计算止损水平

        Args:
            symbol: 股票代码
            entry_price: 入场价格
            direction: 交易方向（long/short）
            atr: 平均真实波幅
            volatility: 波动率

        Returns:
            止损水平
        """
        # 基础止损
        if self.use_atr and atr is not None:
            # 使用ATR计算止损
            stop_distance = atr * self.atr_multiplier
            stop_pct = stop_distance / entry_price
        elif volatility is not None:
            # 使用波动率计算止损（2倍波动率）
            stop_pct = volatility * 2
        else:
            # 使用默认止损
            stop_pct = self.default_stop_pct

        # 计算止损价格
        if direction == 'long':
            stop_price = entry_price * (1 - stop_pct)
        else:  # short
            stop_price = entry_price * (1 + stop_pct)

        level = StopLossLevel(
            symbol=symbol,
            entry_price=entry_price,
            stop_price=stop_price,
            stop_pct=stop_pct,
            stop_type='volatility' if (atr or volatility) else 'fixed',
            last_update=datetime.now()
        )

        self.stop_levels[symbol] = level

        logger.info(
            f"Set {level.stop_type} stop loss for {symbol}: "
            f"entry={entry_price:.2f}, stop={stop_price:.2f} ({stop_pct*100:.2f}%)"
        )

        return level

    def check_stop_loss(
        self,
        symbol: str,
        current_price: float
    ) -> Dict[str, any]:
        """
        检查是否触及止损

        Args:
            symbol: 股票代码
            current_price: 当前价格

        Returns:
            检查结果
        """
        if symbol not in self.stop_levels:
            return {
                'triggered': False,
                'reason': 'No stop loss set'
            }

        level = self.stop_levels[symbol]

        # 判断是多头还是空头（通过止损价格与入场价格的关系）
        is_long = level.stop_price < level.entry_price

        triggered = False
        if is_long:
            # 多头：当前价格 <= 止损价格
            triggered = current_price <= level.stop_price
        else:
            # 空头：当前价格 >= 止损价格
            triggered = current_price >= level.stop_price

        if triggered:
            loss_pct = abs(current_price - level.entry_price) / level.entry_price

            logger.warning(
                f"Stop loss triggered for {symbol}: "
                f"price={current_price:.2f}, stop={level.stop_price:.2f}, "
                f"loss={loss_pct*100:.2f}%"
            )

            return {
                'triggered': True,
                'symbol': symbol,
                'current_price': current_price,
                'stop_price': level.stop_price,
                'entry_price': level.entry_price,
                'loss_pct': loss_pct,
                'stop_type': level.stop_type
            }

        return {
            'triggered': False,
            'distance_to_stop': abs(current_price - level.stop_price),
            'distance_pct': abs(current_price - level.stop_price) / current_price
        }

    def update_stop_loss(
        self,
        symbol: str,
        new_stop_price: float,
        stop_type: str = 'manual'
    ):
        """
        手动更新止损价格

        Args:
            symbol: 股票代码
            new_stop_price: 新止损价格
            stop_type: 止损类型
        """
        if symbol in self.stop_levels:
            level = self.stop_levels[symbol]
            old_stop = level.stop_price

            level.stop_price = new_stop_price
            level.stop_pct = abs(new_stop_price - level.entry_price) / level.entry_price
            level.stop_type = stop_type
            level.last_update = datetime.now()

            logger.info(
                f"Updated stop loss for {symbol}: "
                f"{old_stop:.2f} -> {new_stop_price:.2f}"
            )

    def remove_stop_loss(self, symbol: str):
        """移除止损"""
        if symbol in self.stop_levels:
            del self.stop_levels[symbol]
            logger.info(f"Removed stop loss for {symbol}")

    def get_stop_level(self, symbol: str) -> Optional[StopLossLevel]:
        """获取止损水平"""
        return self.stop_levels.get(symbol)


class TrailingStop:
    """
    追踪止损

    根据有利价格移动自动调整止损位
    """

    def __init__(
        self,
        trailing_pct: float = 0.03,  # 3%追踪止损
        min_profit_to_activate: float = 0.01  # 至少1%盈利才激活
    ):
        """
        初始化追踪止损

        Args:
            trailing_pct: 追踪百分比
            min_profit_to_activate: 激活追踪止损的最小盈利
        """
        self.trailing_pct = trailing_pct
        self.min_profit_to_activate = min_profit_to_activate
        self.trailing_stops: Dict[str, Dict] = {}

    def initialize_trailing_stop(
        self,
        symbol: str,
        entry_price: float,
        direction: str,  # 'long' or 'short'
        initial_stop_price: float
    ):
        """
        初始化追踪止损

        Args:
            symbol: 股票代码
            entry_price: 入场价格
            direction: 交易方向
            initial_stop_price: 初始止损价格
        """
        self.trailing_stops[symbol] = {
            'entry_price': entry_price,
            'direction': direction,
            'stop_price': initial_stop_price,
            'highest_price': entry_price if direction == 'long' else entry_price,
            'lowest_price': entry_price if direction == 'short' else entry_price,
            'activated': False,
            'last_update': datetime.now()
        }

        logger.info(
            f"Initialized trailing stop for {symbol}: "
            f"entry={entry_price:.2f}, initial_stop={initial_stop_price:.2f}"
        )

    def update_trailing_stop(
        self,
        symbol: str,
        current_price: float
    ) -> Dict[str, any]:
        """
        更新追踪止损

        Args:
            symbol: 股票代码
            current_price: 当前价格

        Returns:
            更新结果
        """
        if symbol not in self.trailing_stops:
            return {
                'updated': False,
                'reason': 'No trailing stop set'
            }

        stop_info = self.trailing_stops[symbol]
        direction = stop_info['direction']
        entry_price = stop_info['entry_price']
        old_stop = stop_info['stop_price']

        updated = False
        new_stop = old_stop

        if direction == 'long':
            # 多头追踪止损
            current_profit_pct = (current_price - entry_price) / entry_price

            # 检查是否激活
            if not stop_info['activated']:
                if current_profit_pct >= self.min_profit_to_activate:
                    stop_info['activated'] = True
                    logger.info(
                        f"Trailing stop activated for {symbol}: "
                        f"profit={current_profit_pct*100:.2f}%"
                    )

            # 更新最高价
            if current_price > stop_info['highest_price']:
                stop_info['highest_price'] = current_price

                # 如果已激活，调整止损
                if stop_info['activated']:
                    new_stop = current_price * (1 - self.trailing_pct)

                    # 只能向上调整，不能向下
                    if new_stop > old_stop:
                        stop_info['stop_price'] = new_stop
                        updated = True

        else:  # short
            # 空头追踪止损
            current_profit_pct = (entry_price - current_price) / entry_price

            # 检查是否激活
            if not stop_info['activated']:
                if current_profit_pct >= self.min_profit_to_activate:
                    stop_info['activated'] = True
                    logger.info(
                        f"Trailing stop activated for {symbol}: "
                        f"profit={current_profit_pct*100:.2f}%"
                    )

            # 更新最低价
            if current_price < stop_info['lowest_price']:
                stop_info['lowest_price'] = current_price

                # 如果已激活，调整止损
                if stop_info['activated']:
                    new_stop = current_price * (1 + self.trailing_pct)

                    # 只能向下调整，不能向上
                    if new_stop < old_stop:
                        stop_info['stop_price'] = new_stop
                        updated = True

        if updated:
            stop_info['last_update'] = datetime.now()

            logger.info(
                f"Trailing stop updated for {symbol}: "
                f"{old_stop:.2f} -> {new_stop:.2f}"
            )

        return {
            'updated': updated,
            'old_stop': old_stop,
            'new_stop': new_stop,
            'current_price': current_price,
            'activated': stop_info['activated']
        }

    def check_trailing_stop(
        self,
        symbol: str,
        current_price: float
    ) -> Dict[str, any]:
        """
        检查追踪止损是否触发

        Args:
            symbol: 股票代码
            current_price: 当前价格

        Returns:
            检查结果
        """
        if symbol not in self.trailing_stops:
            return {'triggered': False}

        stop_info = self.trailing_stops[symbol]
        stop_price = stop_info['stop_price']
        direction = stop_info['direction']

        triggered = False

        if direction == 'long':
            triggered = current_price <= stop_price
        else:  # short
            triggered = current_price >= stop_price

        if triggered:
            entry_price = stop_info['entry_price']
            pnl_pct = (
                (current_price - entry_price) / entry_price
                if direction == 'long'
                else (entry_price - current_price) / entry_price
            )

            logger.warning(
                f"Trailing stop triggered for {symbol}: "
                f"price={current_price:.2f}, stop={stop_price:.2f}, "
                f"PnL={pnl_pct*100:.2f}%"
            )

            return {
                'triggered': True,
                'symbol': symbol,
                'current_price': current_price,
                'stop_price': stop_price,
                'entry_price': entry_price,
                'pnl_pct': pnl_pct,
                'highest_price': stop_info.get('highest_price'),
                'lowest_price': stop_info.get('lowest_price')
            }

        return {'triggered': False}


class TimeBasedStopLoss:
    """
    时间止损

    在指定时间后自动平仓
    """

    def __init__(self):
        """初始化时间止损"""
        self.time_stops: Dict[str, datetime] = {}

    def set_time_stop(
        self,
        symbol: str,
        stop_time: datetime
    ):
        """
        设置时间止损

        Args:
            symbol: 股票代码
            stop_time: 止损时间
        """
        self.time_stops[symbol] = stop_time
        logger.info(f"Set time stop for {symbol} at {stop_time}")

    def check_time_stop(self, symbol: str) -> bool:
        """
        检查时间止损

        Args:
            symbol: 股票代码

        Returns:
            是否触发时间止损
        """
        if symbol not in self.time_stops:
            return False

        now = datetime.now()
        stop_time = self.time_stops[symbol]

        if now >= stop_time:
            logger.warning(
                f"Time stop triggered for {symbol} at {now}"
            )
            return True

        return False
