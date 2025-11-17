"""订单执行服务"""

import logging
import time
import threading
from typing import Dict, Any, List
from datetime import datetime

from ..core.state import TradeState
from ..models.schemas import OrderRequest, Action
from ..utils.retry import retry_on_failure

logger = logging.getLogger(__name__)


class OrderExecutor:
    """
    订单执行器

    负责下单、平仓等操作
    """

    def __init__(
        self,
        client,
        state: TradeState,
        exchange: str = "NSE",
        product: str = "MIS"
    ):
        """
        初始化订单执行器

        Args:
            client: OpenAlgo客户端
            state: 交易状态管理器
            exchange: 交易所
            product: 产品类型（MIS=日内）
        """
        self.client = client
        self.state = state
        self.exchange = exchange
        self.product = product

    @retry_on_failure(max_attempts=2, delay=0.5, backoff=2.0)
    def place_market_order(
        self,
        symbol: str,
        action: str,
        quantity: int,
        reason: str
    ) -> Dict[str, Any]:
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
        try:
            if quantity <= 0:
                return {
                    "success": False,
                    "error": f"Invalid quantity: {quantity}",
                    "symbol": symbol
                }

            logger.info(f"Placing {action} order: {symbol} x{quantity} ({reason})")

            # 下单
            response = self.client.placeorder(
                strategy="AI Agent",
                symbol=symbol,
                action=action,
                exchange=self.exchange,
                price_type="MARKET",
                product=self.product,
                quantity=quantity
            )

            if response.get("status") != "success":
                logger.error(f"❌ Order failed: {symbol} {action}: {response.get('message')}")
                return {
                    "success": False,
                    "error": response.get("message"),
                    "symbol": symbol
                }

            order_id = response["orderid"]
            logger.info(f"✓ Order placed: {symbol} {action} x{quantity} → Order#{order_id}")

            # 更新状态
            self.state.increment_trade_count(symbol)
            self.state.add_trade_history({
                "symbol": symbol,
                "action": action,
                "quantity": quantity,
                "order_id": order_id,
                "reason": reason,
                "status": "completed"
            })

            return {
                "success": True,
                "order_id": order_id,
                "symbol": symbol,
                "action": action,
                "quantity": quantity,
                "reason": reason,
                "status": "completed"
            }

        except Exception as e:
            logger.error(f"❌ Order execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol
            }

    def place_bulk_orders(self, orders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量下单（并行）

        Args:
            orders: 订单列表 [{"symbol": "ICICIBANK", "action": "BUY", "quantity": 7, "reason": "..."}, ...]

        Returns:
            批量下单结果
        """
        if not orders:
            return {
                "success": True,
                "total_orders": 0,
                "successful": 0,
                "results": []
            }

        logger.info(f"Placing {len(orders)} orders in parallel...")

        results = {}
        threads = []

        def place_single_order(order_data: dict, results: dict, index: int):
            """在线程中下单"""
            try:
                symbol = order_data["symbol"]
                action = order_data["action"]
                quantity = order_data["quantity"]
                reason = order_data.get("reason", "bulk order")

                result = self.place_market_order(symbol, action, quantity, reason)
                results[index] = result

            except Exception as e:
                logger.error(f"Thread error: {e}")
                results[index] = {
                    "symbol": order_data.get("symbol", "unknown"),
                    "success": False,
                    "error": str(e)
                }

        # 创建线程并下单
        for i, order_data in enumerate(orders):
            thread = threading.Thread(target=place_single_order, args=(order_data, results, i))
            thread.start()
            threads.append(thread)

            # 每2个订单延迟0.5秒（避免限流）
            if (i + 1) % 2 == 0 and (i + 1) < len(orders):
                time.sleep(0.5)

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 统计结果
        success_count = sum(1 for r in results.values() if r.get("success"))
        logger.info(f"✓ Bulk orders: {success_count}/{len(orders)} successful")

        return {
            "success": True,
            "total_orders": len(orders),
            "successful": success_count,
            "results": [results[i] for i in sorted(results.keys())]
        }

    def square_off_all_positions(self) -> Dict[str, Any]:
        """
        平仓所有持仓

        Returns:
            平仓结果
        """
        try:
            logger.info("Squaring off all positions...")

            # 获取持仓
            positions_response = self.client.positionbook()

            if positions_response.get("status") != "success":
                logger.error(f"Failed to get positions: {positions_response}")
                return {
                    "success": False,
                    "error": "Failed to get positions"
                }

            positions = positions_response.get("data", [])
            logger.info(f"Found {len(positions)} positions")

            closed_positions = []
            failed_positions = []

            for position in positions:
                symbol = position.get("symbol")
                quantity = int(float(position.get("quantity", 0)))
                exchange = position.get("exchange", self.exchange)
                product = position.get("product", self.product)

                # 跳过无仓位
                if quantity == 0:
                    logger.debug(f"{symbol}: No position to close (qty=0)")
                    continue

                # 确定平仓方向
                if quantity > 0:
                    # 多头 → 卖出
                    action = "SELL"
                    close_qty = quantity
                else:
                    # 空头 → 买入
                    action = "BUY"
                    close_qty = abs(quantity)

                logger.info(f"Closing {symbol}: {quantity} qty with {action} {close_qty}")

                try:
                    # 下平仓单
                    order_response = self.client.placeorder(
                        strategy="AI Agent",
                        symbol=symbol,
                        action=action,
                        exchange=exchange,
                        price_type="MARKET",
                        product=product,
                        quantity=close_qty
                    )

                    if order_response.get("status") == "success":
                        order_id = order_response.get("orderid")
                        logger.info(f"✓ {symbol}: Order#{order_id} placed to close position")
                        closed_positions.append({
                            "symbol": symbol,
                            "quantity": quantity,
                            "action": action,
                            "order_id": order_id
                        })
                    else:
                        logger.error(f"❌ {symbol}: Failed to place order - {order_response}")
                        failed_positions.append({
                            "symbol": symbol,
                            "error": order_response
                        })

                except Exception as e:
                    logger.error(f"❌ {symbol}: Exception - {e}")
                    failed_positions.append({
                        "symbol": symbol,
                        "error": str(e)
                    })

            # 记录到历史
            self.state.add_trade_history({
                "action": "SQUARE_OFF_ALL",
                "reason": "Market closing - square off all positions",
                "status": "completed",
                "closed_positions": closed_positions,
                "failed_positions": failed_positions
            })

            logger.info(f"✓ Square off complete: Closed {len(closed_positions)}, Failed {len(failed_positions)}")

            return {
                "success": True,
                "action": "square_off",
                "closed_count": len(closed_positions),
                "failed_count": len(failed_positions),
                "closed_positions": closed_positions,
                "failed_positions": failed_positions
            }

        except Exception as e:
            logger.error(f"❌ Square off failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def cancel_all_pending_orders(self) -> Dict[str, Any]:
        """
        取消所有挂单

        Returns:
            取消结果
        """
        try:
            logger.info("Canceling all pending orders...")

            response = self.client.cancelallorder(strategy="AI Agent")

            logger.info(f"Cancel response: {response}")

            # 记录到历史
            self.state.add_trade_history({
                "action": "CANCEL_ALL_ORDERS",
                "reason": "Market closing - cancel pending orders",
                "status": "completed",
                "response": response
            })

            return {
                "success": True,
                "action": "cancel_orders",
                "response": response
            }

        except Exception as e:
            logger.error(f"❌ Cancel orders failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
