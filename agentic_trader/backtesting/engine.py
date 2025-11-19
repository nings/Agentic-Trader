"""回测引擎核心"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """交易记录"""
    timestamp: datetime
    symbol: str
    action: str  # BUY/SELL
    quantity: int
    price: float
    commission: float = 0.0

    @property
    def value(self) -> float:
        """交易价值"""
        return self.quantity * self.price


@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: int  # 正数=多头，负数=空头
    avg_price: float
    current_price: float = 0.0

    @property
    def market_value(self) -> float:
        """市值"""
        return abs(self.quantity) * self.current_price

    @property
    def pnl(self) -> float:
        """盈亏"""
        if self.quantity > 0:  # 多头
            return (self.current_price - self.avg_price) * self.quantity
        else:  # 空头
            return (self.avg_price - self.current_price) * abs(self.quantity)

    @property
    def pnl_percent(self) -> float:
        """盈亏百分比"""
        if self.avg_price == 0:
            return 0.0
        return (self.pnl / (self.avg_price * abs(self.quantity))) * 100


@dataclass
class BacktestResult:
    """回测结果"""
    # 基本信息
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float

    # 交易统计
    total_trades: int
    winning_trades: int
    losing_trades: int

    # 收益指标
    total_return: float
    total_return_pct: float
    annual_return_pct: float

    # 风险指标
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_pct: float

    # 其他指标
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float

    # 时间序列数据
    equity_curve: pd.Series = field(default_factory=pd.Series)
    daily_returns: pd.Series = field(default_factory=pd.Series)
    trade_log: List[Trade] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "initial_capital": self.initial_capital,
            "final_capital": self.final_capital,
            "total_return": self.total_return,
            "total_return_pct": self.total_return_pct,
            "annual_return_pct": self.annual_return_pct,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_pct": self.max_drawdown_pct,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "profit_factor": self.profit_factor
        }


class BacktestEngine:
    """
    专业回测引擎

    支持多策略、多资产回测，提供详细的性能指标
    """

    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_rate: float = 0.001,  # 0.1%手续费
        slippage: float = 0.0005  # 0.05%滑点
    ):
        """
        初始化回测引擎

        Args:
            initial_capital: 初始资金
            commission_rate: 手续费率
            slippage: 滑点
        """
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage

        # 运行时状态
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trade_log: List[Trade] = []
        self.equity_history: List[float] = []
        self.timestamp_history: List[datetime] = []

        logger.info(f"Backtest engine initialized: Capital={initial_capital:,.2f}")

    def execute_trade(
        self,
        timestamp: datetime,
        symbol: str,
        action: str,
        quantity: int,
        price: float
    ) -> Optional[Trade]:
        """
        执行交易

        Args:
            timestamp: 时间戳
            symbol: 股票代码
            action: BUY/SELL
            quantity: 数量
            price: 价格

        Returns:
            交易记录或None（如果失败）
        """
        # 应用滑点
        if action == "BUY":
            execution_price = price * (1 + self.slippage)
        else:
            execution_price = price * (1 - self.slippage)

        # 计算成本
        trade_value = quantity * execution_price
        commission = trade_value * self.commission_rate
        total_cost = trade_value + commission

        # 检查资金
        if action == "BUY" and total_cost > self.cash:
            logger.warning(f"Insufficient cash: Need {total_cost:.2f}, Have {self.cash:.2f}")
            return None

        # 执行交易
        if action == "BUY":
            self._execute_buy(symbol, quantity, execution_price)
            self.cash -= total_cost
        else:
            self._execute_sell(symbol, quantity, execution_price)
            self.cash += trade_value - commission

        # 记录交易
        trade = Trade(
            timestamp=timestamp,
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=execution_price,
            commission=commission
        )
        self.trade_log.append(trade)

        logger.debug(f"Trade executed: {action} {symbol} x{quantity} @ {execution_price:.2f}")

        return trade

    def _execute_buy(self, symbol: str, quantity: int, price: float):
        """执行买入"""
        if symbol in self.positions:
            pos = self.positions[symbol]
            if pos.quantity < 0:
                # 平空头仓位
                if quantity <= abs(pos.quantity):
                    pos.quantity += quantity
                    if pos.quantity == 0:
                        del self.positions[symbol]
                    return
                else:
                    # 部分平仓后开多仓
                    remaining = quantity - abs(pos.quantity)
                    del self.positions[symbol]
                    quantity = remaining

            # 增加多头仓位（或新建）
            total_qty = pos.quantity + quantity
            avg_price = (pos.avg_price * pos.quantity + price * quantity) / total_qty
            pos.quantity = total_qty
            pos.avg_price = avg_price
        else:
            # 新建多头仓位
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                avg_price=price
            )

    def _execute_sell(self, symbol: str, quantity: int, price: float):
        """执行卖出"""
        if symbol in self.positions:
            pos = self.positions[symbol]
            if pos.quantity > 0:
                # 平多头仓位
                if quantity <= pos.quantity:
                    pos.quantity -= quantity
                    if pos.quantity == 0:
                        del self.positions[symbol]
                    return
                else:
                    # 部分平仓后开空仓
                    remaining = quantity - pos.quantity
                    del self.positions[symbol]
                    quantity = remaining

            # 增加空头仓位（或新建）
            total_qty = abs(pos.quantity) + quantity
            avg_price = (pos.avg_price * abs(pos.quantity) + price * quantity) / total_qty
            pos.quantity = -total_qty
            pos.avg_price = avg_price
        else:
            # 新建空头仓位
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=-quantity,
                avg_price=price
            )

    def update_prices(self, timestamp: datetime, prices: Dict[str, float]):
        """
        更新价格并记录权益

        Args:
            timestamp: 时间戳
            prices: 股票价格字典 {symbol: price}
        """
        # 更新持仓价格
        for symbol, pos in self.positions.items():
            if symbol in prices:
                pos.current_price = prices[symbol]

        # 计算总权益
        equity = self.cash + sum(pos.market_value for pos in self.positions.values())

        # 记录历史
        self.equity_history.append(equity)
        self.timestamp_history.append(timestamp)

    def get_portfolio_value(self) -> float:
        """获取当前组合价值"""
        return self.cash + sum(pos.market_value for pos in self.positions.values())

    def calculate_metrics(self) -> BacktestResult:
        """
        计算回测指标

        Returns:
            回测结果
        """
        if not self.equity_history:
            raise ValueError("No equity history available")

        # 基本信息
        start_date = self.timestamp_history[0]
        end_date = self.timestamp_history[-1]
        final_capital = self.equity_history[-1]

        # 收益计算
        total_return = final_capital - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100

        # 年化收益
        days = (end_date - start_date).days
        years = days / 365.25
        annual_return_pct = ((final_capital / self.initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0

        # 日收益率
        equity_series = pd.Series(self.equity_history, index=self.timestamp_history)
        daily_returns = equity_series.pct_change().dropna()

        # Sharpe比率（假设无风险利率=0）
        if len(daily_returns) > 1 and daily_returns.std() > 0:
            sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
        else:
            sharpe_ratio = 0.0

        # 最大回撤
        cumulative = equity_series
        running_max = cumulative.cummax()
        drawdown = cumulative - running_max
        max_drawdown = drawdown.min()
        max_drawdown_pct = (max_drawdown / running_max[drawdown.idxmin()]) * 100 if len(running_max) > 0 else 0

        # 交易统计
        winning_trades = [t for t in self.trade_log if self._calculate_trade_pnl(t) > 0]
        losing_trades = [t for t in self.trade_log if self._calculate_trade_pnl(t) < 0]

        total_trades = len(self.trade_log)
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

        avg_win = np.mean([self._calculate_trade_pnl(t) for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([self._calculate_trade_pnl(t) for t in losing_trades]) if losing_trades else 0

        # 盈亏比
        total_win = sum([self._calculate_trade_pnl(t) for t in winning_trades])
        total_loss = abs(sum([self._calculate_trade_pnl(t) for t in losing_trades]))
        profit_factor = (total_win / total_loss) if total_loss > 0 else 0

        return BacktestResult(
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            total_trades=total_trades,
            winning_trades=win_count,
            losing_trades=loss_count,
            total_return=total_return,
            total_return_pct=total_return_pct,
            annual_return_pct=annual_return_pct,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            equity_curve=equity_series,
            daily_returns=daily_returns,
            trade_log=self.trade_log
        )

    def _calculate_trade_pnl(self, trade: Trade) -> float:
        """计算交易盈亏（简化版）"""
        # 这里简化处理，实际应该匹配买卖对
        return 0.0

    def reset(self):
        """重置回测引擎"""
        self.cash = self.initial_capital
        self.positions.clear()
        self.trade_log.clear()
        self.equity_history.clear()
        self.timestamp_history.clear()
        logger.info("Backtest engine reset")
