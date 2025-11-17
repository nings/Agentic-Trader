"""线程安全的交易状态管理"""

import json
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, List, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class TradeState:
    """
    线程安全的交易状态管理器

    Attributes:
        daily_pnl: 当日盈亏
        trade_counts: 每个股票的交易次数
        trade_history: 交易历史记录
        active_positions: 当前持仓
        stop_loss_hit: 是否触发止损
        squared_off_today: 今天是否已平仓
    """

    daily_pnl: float = 0.0
    trade_counts: Dict[str, int] = field(default_factory=dict)
    trade_history: List[Dict[str, Any]] = field(default_factory=list)
    active_positions: Dict[str, Dict] = field(default_factory=dict)
    stop_loss_hit: bool = False
    squared_off_today: bool = False
    _lock: Lock = field(default_factory=Lock, repr=False)

    def update_pnl(self, amount: float) -> None:
        """
        线程安全的盈亏更新

        Args:
            amount: 盈亏金额
        """
        with self._lock:
            old_pnl = self.daily_pnl
            self.daily_pnl = amount
            logger.info(f"PnL updated: {old_pnl:.2f} -> {self.daily_pnl:.2f}")
            self._log_state_change("pnl_update", {"old": old_pnl, "new": amount})

    def increment_trade_count(self, symbol: str) -> None:
        """
        线程安全的交易计数增加

        Args:
            symbol: 股票代码
        """
        with self._lock:
            self.trade_counts[symbol] = self.trade_counts.get(symbol, 0) + 1
            logger.debug(f"Trade count for {symbol}: {self.trade_counts[symbol]}")
            self._log_state_change("trade_count_increment", {"symbol": symbol})

    def get_trade_count(self, symbol: str) -> int:
        """
        获取股票的交易次数

        Args:
            symbol: 股票代码

        Returns:
            交易次数
        """
        with self._lock:
            return self.trade_counts.get(symbol, 0)

    def add_trade_history(self, trade: Dict[str, Any]) -> None:
        """
        添加交易历史记录

        Args:
            trade: 交易记录
        """
        with self._lock:
            self.trade_history.append({
                **trade,
                "timestamp": datetime.now().isoformat()
            })
            logger.info(f"Trade history added: {trade.get('symbol')} {trade.get('action')}")

    def set_stop_loss_hit(self, hit: bool) -> None:
        """
        设置止损触发状态

        Args:
            hit: 是否触发
        """
        with self._lock:
            old_value = self.stop_loss_hit
            self.stop_loss_hit = hit
            if hit and not old_value:
                logger.warning("⚠️ Stop loss triggered!")
                self._log_state_change("stop_loss_triggered", {"daily_pnl": self.daily_pnl})

    def set_squared_off_today(self, squared: bool) -> None:
        """
        设置平仓状态

        Args:
            squared: 是否已平仓
        """
        with self._lock:
            self.squared_off_today = squared
            if squared:
                logger.info("✓ All positions squared off")
                self._log_state_change("squared_off", {})

    def reset_daily_state(self) -> None:
        """重置每日状态"""
        with self._lock:
            final_pnl = self.daily_pnl
            total_trades = sum(self.trade_counts.values())

            logger.info(f"Daily reset - Final PnL: Rs.{final_pnl:.2f}, Total trades: {total_trades}")

            self.daily_pnl = 0.0
            self.trade_counts.clear()
            self.stop_loss_hit = False
            self.squared_off_today = False

            self._log_state_change("daily_reset", {
                "final_pnl": final_pnl,
                "total_trades": total_trades
            })

    def _log_state_change(self, action: str, data: Any) -> None:
        """
        记录状态变更（审计日志）

        Args:
            action: 操作类型
            data: 操作数据
        """
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "data": data,
                "state_snapshot": self.to_dict()
            }
            # 写入审计日志
            with open("logs/state_audit.jsonl", "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """
        序列化状态为字典

        Returns:
            状态字典
        """
        return {
            "daily_pnl": self.daily_pnl,
            "trade_counts": dict(self.trade_counts),
            "stop_loss_hit": self.stop_loss_hit,
            "squared_off_today": self.squared_off_today,
            "total_trades": len(self.trade_history)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradeState':
        """
        从字典反序列化状态

        Args:
            data: 状态字典

        Returns:
            TradeState实例
        """
        return cls(
            daily_pnl=data.get("daily_pnl", 0.0),
            trade_counts=data.get("trade_counts", {}),
            stop_loss_hit=data.get("stop_loss_hit", False),
            squared_off_today=data.get("squared_off_today", False)
        )

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"TradeState(pnl={self.daily_pnl:.2f}, "
            f"trades={sum(self.trade_counts.values())}, "
            f"stop_loss={self.stop_loss_hit})"
        )
