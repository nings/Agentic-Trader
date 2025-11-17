"""风险管理服务"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from ..core.state import TradeState
from ..models.schemas import Action, RiskCheckRequest, RiskCheckResponse
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class RiskManager:
    """
    风险管理器

    负责验证交易是否符合风险管理规则
    """

    def __init__(
        self,
        client,
        state: TradeState,
        max_trades_per_symbol: int = 5,
        daily_stop_loss: float = -10000.0,
        square_off_hour: int = 15,
        square_off_minute: int = 15
    ):
        """
        初始化风险管理器

        Args:
            client: OpenAlgo客户端
            state: 交易状态管理器
            max_trades_per_symbol: 每只股票每天最大交易次数
            daily_stop_loss: 每日止损限制
            square_off_hour: 平仓时间（小时）
            square_off_minute: 平仓时间（分钟）
        """
        self.client = client
        self.state = state
        self.max_trades_per_symbol = max_trades_per_symbol
        self.daily_stop_loss = daily_stop_loss
        self.square_off_hour = square_off_hour
        self.square_off_minute = square_off_minute

    def check_constraints(self, symbol: str, action: str) -> Dict[str, Any]:
        """
        验证交易是否符合风险规则

        Args:
            symbol: 股票代码
            action: 交易动作（BUY/SELL）

        Returns:
            风险检查结果 {"allowed": bool, "reason": str}
        """
        logger.debug(f"Risk check: {action} {symbol}")

        # 1. 检查止损
        if self.state.stop_loss_hit:
            logger.warning(f"❌ Risk check failed: Daily loss limit reached")
            return {
                "allowed": False,
                "reason": "Daily loss limit reached - no new trades",
                "symbol": symbol,
                "action": action
            }

        if self.state.daily_pnl <= self.daily_stop_loss:
            self.state.set_stop_loss_hit(True)
            logger.warning(f"❌ Stop-loss hit: Rs.{self.state.daily_pnl:.2f}")
            return {
                "allowed": False,
                "reason": f"Daily stop-loss hit (Rs.{self.state.daily_pnl:.2f})",
                "symbol": symbol,
                "action": action
            }

        # 2. 检查交易次数限制
        trade_count = self.state.get_trade_count(symbol)
        if trade_count >= self.max_trades_per_symbol:
            logger.warning(f"❌ Max trades reached for {symbol}: {trade_count}/{self.max_trades_per_symbol}")
            return {
                "allowed": False,
                "reason": f"Max trades reached for {symbol} ({self.max_trades_per_symbol}/day)",
                "symbol": symbol,
                "action": action
            }

        # 3. 检查仓位（禁止加仓）
        position_check = self._check_position_constraint(symbol, action)
        if not position_check["allowed"]:
            return position_check

        # 4. 检查时间限制
        time_check = self._check_time_constraint()
        if not time_check["allowed"]:
            return {**time_check, "symbol": symbol, "action": action}

        logger.debug(f"✓ Risk check passed: {action} {symbol}")
        return {
            "allowed": True,
            "reason": "All risk checks passed",
            "symbol": symbol,
            "action": action
        }

    def _check_position_constraint(self, symbol: str, action: str) -> Dict[str, Any]:
        """
        检查仓位限制（禁止加仓）

        Args:
            symbol: 股票代码
            action: 交易动作

        Returns:
            检查结果
        """
        try:
            response = self.client.positionbook()

            if response.get("status") != "success":
                logger.warning(f"Failed to check positions: {response}")
                return {"allowed": True, "reason": "Position check skipped (API error)"}

            # 查找当前持仓
            position_qty = 0
            for pos in response["data"]:
                if pos["symbol"] == symbol and int(pos["quantity"]) != 0:
                    position_qty = int(pos["quantity"])
                    break

            # 检查是否尝试加仓
            if action == "BUY" and position_qty > 0:
                # 已有多头仓位，不能再买入
                logger.warning(f"❌ Cannot BUY {symbol} - Already have long position (Qty: {position_qty})")
                return {
                    "allowed": False,
                    "reason": f"Already have long position in {symbol} (Qty: {position_qty}). Must close first."
                }
            elif action == "SELL" and position_qty < 0:
                # 已有空头仓位，不能再卖出
                logger.warning(f"❌ Cannot SELL {symbol} - Already have short position (Qty: {position_qty})")
                return {
                    "allowed": False,
                    "reason": f"Already have short position in {symbol} (Qty: {position_qty}). Must close first."
                }

            # 允许的情况：
            # - BUY: 无仓位或有空头仓位（平仓）
            # - SELL: 无仓位（做空）或有多头仓位（平仓）
            return {"allowed": True, "reason": "Position check passed"}

        except Exception as e:
            logger.error(f"Error checking positions for {symbol}: {e}")
            # 出错时允许交易，避免阻塞
            return {"allowed": True, "reason": "Position check skipped (error)"}

    def _check_time_constraint(self) -> Dict[str, bool]:
        """
        检查时间限制

        Returns:
            检查结果
        """
        now = datetime.now()

        if now.hour >= self.square_off_hour and now.minute >= self.square_off_minute:
            logger.warning(f"❌ Market closing time - no new trades after {self.square_off_hour}:{self.square_off_minute:02d}")
            return {
                "allowed": False,
                "reason": f"Market closing time - no new trades after {self.square_off_hour}:{self.square_off_minute:02d} PM"
            }

        return {"allowed": True, "reason": "Time check passed"}

    def check_multiple_constraints(self, trades: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        批量检查多个交易的风险

        Args:
            trades: 交易列表 [{"symbol": "ICICIBANK", "action": "BUY"}, ...]

        Returns:
            检查结果列表
        """
        logger.info(f"Bulk risk check: {len(trades)} trades")

        results = []
        for trade in trades:
            symbol = trade["symbol"]
            action = trade["action"]
            result = self.check_constraints(symbol, action)
            results.append(result)

        allowed_count = sum(1 for r in results if r["allowed"])
        logger.info(f"Bulk risk check: {allowed_count}/{len(trades)} trades allowed")

        return results

    def calculate_position_size(
        self,
        symbol: str,
        ltp: float,
        max_investment: float = 10000.0
    ) -> Dict[str, Any]:
        """
        计算仓位大小

        Args:
            symbol: 股票代码
            ltp: 当前价格
            max_investment: 最大投资金额

        Returns:
            仓位计算结果
        """
        try:
            if ltp <= 0:
                return {
                    "error": f"Invalid LTP {ltp}. LTP must be positive.",
                    "symbol": symbol,
                    "quantity": 0,
                    "success": False
                }

            # 计算数量
            quantity = int(max_investment / ltp)

            if quantity == 0:
                return {
                    "error": f"LTP {ltp} too high for max_investment {max_investment}. Quantity would be 0.",
                    "symbol": symbol,
                    "quantity": 0,
                    "ltp": ltp,
                    "success": False
                }

            # 实际投资额
            actual_investment = quantity * ltp

            logger.debug(f"Position calc for {symbol}: LTP={ltp}, Qty={quantity}, Investment=Rs.{actual_investment:.2f}")

            return {
                "symbol": symbol,
                "ltp": round(ltp, 2),
                "quantity": quantity,
                "max_investment": max_investment,
                "actual_investment": round(actual_investment, 2),
                "formula": f"int({max_investment} / {ltp}) = {quantity}",
                "success": True
            }

        except Exception as e:
            logger.error(f"Position calculation failed for {symbol}: {e}")
            return {
                "error": str(e),
                "symbol": symbol,
                "quantity": 0,
                "success": False
            }

    def calculate_multiple_positions(
        self,
        positions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        批量计算仓位大小

        Args:
            positions: 仓位列表 [{"symbol": "ICICIBANK", "ltp": 1350.0}, ...]

        Returns:
            计算结果列表
        """
        logger.debug(f"Bulk position calc: {len(positions)} symbols")

        results = []
        for pos in positions:
            symbol = pos["symbol"]
            ltp = pos["ltp"]
            max_investment = pos.get("max_investment", 10000.0)

            result = self.calculate_position_size(symbol, ltp, max_investment)
            results.append(result)

        return results
