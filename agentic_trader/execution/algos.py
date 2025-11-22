"""执行算法 - TWAP、VWAP、智能路由"""

import logging
import time
import threading
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """执行结果"""
    symbol: str
    total_quantity: int
    executed_quantity: int
    avg_price: float
    total_cost: float
    slices: List[Dict[str, Any]]
    start_time: datetime
    end_time: datetime
    success: bool
    error: Optional[str] = None


class TWAPExecutor:
    """
    时间加权平均价格（TWAP）执行器

    将大订单分割成多个小订单，在指定时间内均匀执行
    """

    def __init__(self, client, order_executor):
        """
        初始化TWAP执行器

        Args:
            client: OpenAlgo客户端
            order_executor: 订单执行器
        """
        self.client = client
        self.order_executor = order_executor

    def execute(
        self,
        symbol: str,
        action: str,
        total_quantity: int,
        duration_minutes: int,
        num_slices: int,
        reason: str = "TWAP execution"
    ) -> ExecutionResult:
        """
        执行TWAP策略

        Args:
            symbol: 股票代码
            action: 交易方向（BUY/SELL）
            total_quantity: 总数量
            duration_minutes: 执行时长（分钟）
            num_slices: 分割片数
            reason: 交易原因

        Returns:
            执行结果
        """
        start_time = datetime.now()

        logger.info(
            f"Starting TWAP execution: {symbol} {action} {total_quantity} "
            f"over {duration_minutes} minutes in {num_slices} slices"
        )

        # 计算每片数量和时间间隔
        slice_quantity = total_quantity // num_slices
        remainder = total_quantity % num_slices
        interval_seconds = (duration_minutes * 60) / num_slices

        slices = []
        executed_quantity = 0
        total_cost = 0.0
        prices = []

        for i in range(num_slices):
            # 最后一片包含余数
            qty = slice_quantity + (remainder if i == num_slices - 1 else 0)

            if qty == 0:
                continue

            try:
                # 执行订单
                result = self.order_executor.place_market_order(
                    symbol=symbol,
                    action=action,
                    quantity=qty,
                    reason=f"{reason} - Slice {i+1}/{num_slices}"
                )

                if result.get("success"):
                    # 获取成交价格（简化处理，实际需要从订单状态获取）
                    price = self._get_execution_price(symbol)

                    executed_quantity += qty
                    cost = qty * price
                    total_cost += cost
                    prices.append(price)

                    slices.append({
                        "slice_num": i + 1,
                        "quantity": qty,
                        "price": price,
                        "timestamp": datetime.now(),
                        "success": True
                    })

                    logger.info(f"Slice {i+1}/{num_slices} executed: {qty} @ {price}")

                else:
                    slices.append({
                        "slice_num": i + 1,
                        "quantity": qty,
                        "timestamp": datetime.now(),
                        "success": False,
                        "error": result.get("error")
                    })

                    logger.error(f"Slice {i+1}/{num_slices} failed: {result.get('error')}")

                # 等待下一个时间片（除了最后一次）
                if i < num_slices - 1:
                    time.sleep(interval_seconds)

            except Exception as e:
                logger.error(f"Error executing slice {i+1}: {e}")
                slices.append({
                    "slice_num": i + 1,
                    "quantity": qty,
                    "timestamp": datetime.now(),
                    "success": False,
                    "error": str(e)
                })

        end_time = datetime.now()

        # 计算平均价格
        avg_price = total_cost / executed_quantity if executed_quantity > 0 else 0.0

        success = executed_quantity == total_quantity

        logger.info(
            f"TWAP execution completed: {executed_quantity}/{total_quantity} "
            f"@ avg {avg_price:.2f}"
        )

        return ExecutionResult(
            symbol=symbol,
            total_quantity=total_quantity,
            executed_quantity=executed_quantity,
            avg_price=avg_price,
            total_cost=total_cost,
            slices=slices,
            start_time=start_time,
            end_time=end_time,
            success=success
        )

    def _get_execution_price(self, symbol: str) -> float:
        """
        获取成交价格

        Args:
            symbol: 股票代码

        Returns:
            成交价格
        """
        try:
            response = self.client.quotes(symbol=symbol, exchange="NSE")
            if response.get("status") == "success":
                return float(response["data"]["ltp"])
        except Exception as e:
            logger.error(f"Error fetching execution price: {e}")

        return 0.0


class VWAPExecutor:
    """
    成交量加权平均价格（VWAP）执行器

    根据历史成交量分布调整订单执行节奏
    """

    def __init__(self, client, order_executor):
        """
        初始化VWAP执行器

        Args:
            client: OpenAlgo客户端
            order_executor: 订单执行器
        """
        self.client = client
        self.order_executor = order_executor

    def execute(
        self,
        symbol: str,
        action: str,
        total_quantity: int,
        duration_minutes: int,
        reason: str = "VWAP execution"
    ) -> ExecutionResult:
        """
        执行VWAP策略

        Args:
            symbol: 股票代码
            action: 交易方向
            total_quantity: 总数量
            duration_minutes: 执行时长
            reason: 交易原因

        Returns:
            执行结果
        """
        start_time = datetime.now()

        logger.info(
            f"Starting VWAP execution: {symbol} {action} {total_quantity} "
            f"over {duration_minutes} minutes"
        )

        # 获取历史成交量分布
        volume_profile = self._get_volume_profile(symbol)

        # 根据成交量分布计算每个时间片的数量
        slices = self._calculate_vwap_slices(
            total_quantity, duration_minutes, volume_profile
        )

        executed_quantity = 0
        total_cost = 0.0
        slice_results = []

        for i, slice_info in enumerate(slices):
            qty = slice_info['quantity']
            wait_time = slice_info['wait_time']

            if qty == 0:
                continue

            try:
                # 执行订单
                result = self.order_executor.place_market_order(
                    symbol=symbol,
                    action=action,
                    quantity=qty,
                    reason=f"{reason} - Slice {i+1}/{len(slices)}"
                )

                if result.get("success"):
                    price = self._get_execution_price(symbol)

                    executed_quantity += qty
                    cost = qty * price
                    total_cost += cost

                    slice_results.append({
                        "slice_num": i + 1,
                        "quantity": qty,
                        "price": price,
                        "timestamp": datetime.now(),
                        "success": True
                    })

                    logger.info(f"VWAP Slice {i+1}/{len(slices)} executed: {qty} @ {price}")

                else:
                    slice_results.append({
                        "slice_num": i + 1,
                        "quantity": qty,
                        "timestamp": datetime.now(),
                        "success": False,
                        "error": result.get("error")
                    })

                # 等待下一个时间片
                if i < len(slices) - 1:
                    time.sleep(wait_time)

            except Exception as e:
                logger.error(f"Error executing VWAP slice {i+1}: {e}")
                slice_results.append({
                    "slice_num": i + 1,
                    "quantity": qty,
                    "timestamp": datetime.now(),
                    "success": False,
                    "error": str(e)
                })

        end_time = datetime.now()

        avg_price = total_cost / executed_quantity if executed_quantity > 0 else 0.0
        success = executed_quantity == total_quantity

        logger.info(
            f"VWAP execution completed: {executed_quantity}/{total_quantity} "
            f"@ avg {avg_price:.2f}"
        )

        return ExecutionResult(
            symbol=symbol,
            total_quantity=total_quantity,
            executed_quantity=executed_quantity,
            avg_price=avg_price,
            total_cost=total_cost,
            slices=slice_results,
            start_time=start_time,
            end_time=end_time,
            success=success
        )

    def _get_volume_profile(self, symbol: str) -> List[float]:
        """
        获取成交量分布

        Args:
            symbol: 股票代码

        Returns:
            成交量权重列表
        """
        # 简化版：使用典型的日内成交量分布模式
        # 实际应从历史数据计算
        # 通常：开盘和收盘时段成交量较大

        typical_profile = [
            0.15,  # 9:15-10:00 开盘高峰
            0.08,  # 10:00-11:00
            0.06,  # 11:00-12:00
            0.05,  # 12:00-13:00 午间低谷
            0.06,  # 13:00-14:00
            0.10,  # 14:00-15:00
            0.20,  # 15:00-15:30 收盘高峰
        ]

        # 标准化
        total = sum(typical_profile)
        return [v / total for v in typical_profile]

    def _calculate_vwap_slices(
        self,
        total_quantity: int,
        duration_minutes: int,
        volume_profile: List[float]
    ) -> List[Dict[str, Any]]:
        """
        根据成交量分布计算订单分片

        Args:
            total_quantity: 总数量
            duration_minutes: 执行时长
            volume_profile: 成交量分布

        Returns:
            分片信息列表
        """
        num_slices = len(volume_profile)
        interval_seconds = (duration_minutes * 60) / num_slices

        slices = []
        allocated = 0

        for i, volume_weight in enumerate(volume_profile):
            # 根据成交量权重分配数量
            if i == num_slices - 1:
                # 最后一片包含所有余数
                qty = total_quantity - allocated
            else:
                qty = int(total_quantity * volume_weight)
                allocated += qty

            slices.append({
                'quantity': qty,
                'wait_time': interval_seconds,
                'volume_weight': volume_weight
            })

        return slices

    def _get_execution_price(self, symbol: str) -> float:
        """获取成交价格"""
        try:
            response = self.client.quotes(symbol=symbol, exchange="NSE")
            if response.get("status") == "success":
                return float(response["data"]["ltp"])
        except Exception as e:
            logger.error(f"Error fetching execution price: {e}")

        return 0.0


class SmartRouter:
    """
    智能订单路由器

    根据市场条件自动选择最佳执行算法
    """

    def __init__(self, client, order_executor):
        """
        初始化智能路由器

        Args:
            client: OpenAlgo客户端
            order_executor: 订单执行器
        """
        self.client = client
        self.order_executor = order_executor
        self.twap_executor = TWAPExecutor(client, order_executor)
        self.vwap_executor = VWAPExecutor(client, order_executor)

    def execute(
        self,
        symbol: str,
        action: str,
        quantity: int,
        max_duration_minutes: int = 30,
        urgency: str = 'normal',
        reason: str = "Smart routing"
    ) -> ExecutionResult:
        """
        智能执行订单

        Args:
            symbol: 股票代码
            action: 交易方向
            quantity: 数量
            max_duration_minutes: 最大执行时长
            urgency: 紧急程度 ('low', 'normal', 'high', 'urgent')
            reason: 交易原因

        Returns:
            执行结果
        """
        logger.info(
            f"Smart routing: {symbol} {action} {quantity}, "
            f"urgency={urgency}, max_duration={max_duration_minutes}min"
        )

        # 获取市场条件
        market_condition = self._analyze_market_condition(symbol)

        # 根据订单大小、紧急程度和市场条件选择执行策略
        strategy = self._select_strategy(
            quantity, urgency, market_condition
        )

        logger.info(f"Selected strategy: {strategy}")

        if strategy == 'immediate':
            # 立即执行（市价单）
            result = self.order_executor.place_market_order(
                symbol=symbol,
                action=action,
                quantity=quantity,
                reason=reason
            )

            return ExecutionResult(
                symbol=symbol,
                total_quantity=quantity,
                executed_quantity=quantity if result.get("success") else 0,
                avg_price=0.0,  # 需要从结果获取
                total_cost=0.0,
                slices=[result],
                start_time=datetime.now(),
                end_time=datetime.now(),
                success=result.get("success", False),
                error=result.get("error")
            )

        elif strategy == 'twap':
            # TWAP执行
            num_slices = self._calculate_optimal_slices(quantity, max_duration_minutes)
            return self.twap_executor.execute(
                symbol=symbol,
                action=action,
                total_quantity=quantity,
                duration_minutes=max_duration_minutes,
                num_slices=num_slices,
                reason=reason
            )

        elif strategy == 'vwap':
            # VWAP执行
            return self.vwap_executor.execute(
                symbol=symbol,
                action=action,
                total_quantity=quantity,
                duration_minutes=max_duration_minutes,
                reason=reason
            )

        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def _analyze_market_condition(self, symbol: str) -> Dict[str, Any]:
        """
        分析市场条件

        Args:
            symbol: 股票代码

        Returns:
            市场条件字典
        """
        try:
            # 获取深度数据
            depth = self.client.depth(symbol=symbol, exchange="NSE")

            if depth.get("status") == "success":
                data = depth["data"]

                total_bid = sum(b["quantity"] for b in data.get("bids", []))
                total_ask = sum(a["quantity"] for a in data.get("asks", []))

                # 计算流动性指标
                liquidity = total_bid + total_ask
                spread_pct = 0.0

                if data.get("bids") and data.get("asks"):
                    best_bid = data["bids"][0]["price"]
                    best_ask = data["asks"][0]["price"]
                    spread_pct = (best_ask - best_bid) / best_ask * 100

                return {
                    'liquidity': liquidity,
                    'spread_pct': spread_pct,
                    'bid_ask_ratio': total_bid / (total_ask + 1),
                    'total_bid': total_bid,
                    'total_ask': total_ask
                }

        except Exception as e:
            logger.error(f"Error analyzing market condition: {e}")

        # 返回默认值
        return {
            'liquidity': 10000,
            'spread_pct': 0.1,
            'bid_ask_ratio': 1.0,
            'total_bid': 5000,
            'total_ask': 5000
        }

    def _select_strategy(
        self,
        quantity: int,
        urgency: str,
        market_condition: Dict[str, Any]
    ) -> str:
        """
        选择执行策略

        Args:
            quantity: 订单数量
            urgency: 紧急程度
            market_condition: 市场条件

        Returns:
            策略名称
        """
        liquidity = market_condition['liquidity']
        spread_pct = market_condition['spread_pct']

        # 订单占流动性的比例
        order_size_ratio = quantity / liquidity if liquidity > 0 else 1.0

        # 决策逻辑
        if urgency == 'urgent':
            return 'immediate'

        elif urgency == 'high':
            if order_size_ratio < 0.1:  # 小订单
                return 'immediate'
            else:
                return 'twap'  # 快速TWAP

        elif urgency == 'normal':
            if order_size_ratio < 0.05:
                return 'immediate'
            elif spread_pct > 0.5:  # 高价差
                return 'twap'  # 避免冲击
            else:
                return 'vwap'  # 跟随成交量

        else:  # 'low'
            return 'vwap'

    def _calculate_optimal_slices(
        self,
        quantity: int,
        duration_minutes: int
    ) -> int:
        """
        计算最优分片数量

        Args:
            quantity: 订单数量
            duration_minutes: 执行时长

        Returns:
            分片数量
        """
        # 根据订单大小和时长计算
        # 一般每片持续2-5分钟

        min_slice_duration = 2  # 分钟
        max_slices = duration_minutes // min_slice_duration

        # 根据数量调整
        if quantity < 10:
            return min(2, max_slices)
        elif quantity < 50:
            return min(5, max_slices)
        elif quantity < 100:
            return min(10, max_slices)
        else:
            return min(20, max_slices)
