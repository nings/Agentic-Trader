"""市场数据服务"""

import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..utils.retry import retry_on_failure
from .indicators import IndicatorCalculator

logger = logging.getLogger(__name__)


class MarketDataService:
    """
    市场数据服务

    负责获取市场报价、深度数据和技术指标
    """

    def __init__(
        self,
        client,
        symbols: List[str],
        exchange: str = "NSE",
        max_workers: int = 10
    ):
        """
        初始化市场数据服务

        Args:
            client: OpenAlgo客户端
            symbols: 股票代码列表
            exchange: 交易所
            max_workers: 最大并发线程数
        """
        self.client = client
        self.symbols = symbols
        self.exchange = exchange
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def fetch_all_market_data(self, timeout: int = 30) -> Dict[str, Any]:
        """
        并发获取所有股票的市场数据

        Args:
            timeout: 超时时间（秒）

        Returns:
            包含所有股票数据的字典
        """
        start_time = time.time()
        logger.info(f"Fetching market data for {len(self.symbols)} symbols in parallel...")

        results = {}
        futures = []

        # 提交所有任务
        for index, symbol in enumerate(self.symbols):
            future = self.executor.submit(
                self._fetch_symbol_data_with_delay,
                symbol,
                index
            )
            futures.append((symbol, future))

        # 收集结果
        for symbol, future in futures:
            try:
                data = future.result(timeout=timeout)
                results[symbol] = data
            except Exception as e:
                logger.error(f"Failed to fetch data for {symbol}: {e}")
                results[symbol] = {"symbol": symbol, "error": str(e)}

        elapsed = time.time() - start_time
        logger.info(f"✓ All market data fetched in {elapsed:.1f}s")

        return {
            "status": "success",
            "data": results,
            "elapsed_seconds": round(elapsed, 1)
        }

    def _fetch_symbol_data_with_delay(self, symbol: str, index: int) -> Dict[str, Any]:
        """
        获取单个股票数据（带延迟避免API限流）

        Args:
            symbol: 股票代码
            index: 索引（用于计算延迟）

        Returns:
            股票数据字典
        """
        # 错峰延迟
        time.sleep(index * 0.2)

        try:
            # 1. 获取报价
            quotes = self.fetch_quotes(symbol)

            # 短暂延迟
            time.sleep(0.15)

            # 2. 获取深度
            depth = self.fetch_depth(symbol)

            # 短暂延迟
            time.sleep(0.15)

            # 3. 计算技术指标
            indicators = self._calculate_indicators(symbol)

            return {
                "symbol": symbol,
                "ltp": quotes.get("ltp", 0),
                "volume": quotes.get("volume", 0),
                "bid_ask_ratio": depth.get("bid_ask_ratio", 0),
                "rsi": indicators["current"]["rsi"],
                "macd_trend": indicators["current"]["macd_trend"],
                "ema_trend": indicators["current"]["ema_trend"]
            }

        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return {"symbol": symbol, "error": str(e)}

    @retry_on_failure(max_attempts=3, delay=1.0, backoff=2.0)
    def fetch_quotes(self, symbol: str) -> Dict[str, Any]:
        """
        获取股票报价

        Args:
            symbol: 股票代码

        Returns:
            报价数据

        Raises:
            ValueError: 如果API返回错误
        """
        logger.debug(f"Fetching quotes for {symbol}")

        response = self.client.quotes(symbol=symbol, exchange=self.exchange)

        if response.get("status") != "success":
            raise ValueError(f"Failed to fetch quotes for {symbol}: {response.get('message')}")

        data = response["data"]
        logger.debug(f"{symbol} Quote: LTP={data['ltp']}, Volume={data['volume']:,}")

        return {
            "symbol": symbol,
            "ltp": data["ltp"],
            "open": data["open"],
            "high": data["high"],
            "low": data["low"],
            "volume": data["volume"],
            "prev_close": data["prev_close"]
        }

    @retry_on_failure(max_attempts=3, delay=1.0, backoff=2.0)
    def fetch_depth(self, symbol: str) -> Dict[str, Any]:
        """
        获取市场深度

        Args:
            symbol: 股票代码

        Returns:
            市场深度数据

        Raises:
            ValueError: 如果API返回错误
        """
        logger.debug(f"Fetching depth for {symbol}")

        response = self.client.depth(symbol=symbol, exchange=self.exchange)

        if response.get("status") != "success":
            raise ValueError(f"Failed to fetch depth for {symbol}: {response.get('message')}")

        data = response["data"]

        # 计算买卖单量
        total_bid = sum(b["quantity"] for b in data["bids"])
        total_ask = sum(a["quantity"] for a in data["asks"])
        bid_ask_ratio = round(total_bid / total_ask, 2) if total_ask > 0 else 0

        logger.debug(f"{symbol} Depth: Bids={total_bid:,}, Asks={total_ask:,}, Ratio={bid_ask_ratio:.2f}")

        return {
            "symbol": symbol,
            "total_bid_qty": total_bid,
            "total_ask_qty": total_ask,
            "bid_ask_ratio": bid_ask_ratio,
            "best_bid": data["bids"][0]["price"] if data["bids"] else 0,
            "best_ask": data["asks"][0]["price"] if data["asks"] else 0
        }

    def _calculate_indicators(self, symbol: str) -> Dict[str, Any]:
        """
        计算技术指标

        Args:
            symbol: 股票代码

        Returns:
            技术指标数据
        """
        calculator = IndicatorCalculator(self.client, symbol, self.exchange)
        return calculator.calculate_all(lookback_bars=5)

    def get_account_funds(self) -> Dict[str, Any]:
        """
        获取账户资金

        Returns:
            资金数据
        """
        try:
            logger.debug("Fetching account funds")

            response = self.client.funds()

            if response.get("status") != "success":
                raise ValueError("Failed to fetch funds")

            data = response["data"]
            cash = float(data.get("availablecash", 0))

            logger.info(f"Available Cash: Rs.{cash:,.2f}")

            return {
                "available_cash": cash,
                "m2m_unrealized": float(data.get("m2munrealized", 0)),
                "m2m_realized": float(data.get("m2mrealized", 0))
            }

        except Exception as e:
            logger.error(f"Error fetching funds: {e}")
            return {"error": str(e)}

    def get_positions(self) -> Dict[str, Any]:
        """
        获取当前持仓

        Returns:
            持仓数据
        """
        try:
            logger.debug("Fetching positions")

            response = self.client.positionbook()

            if response.get("status") != "success":
                raise ValueError("Failed to fetch positions")

            positions = {}
            for pos in response["data"]:
                if int(pos["quantity"]) != 0:
                    positions[pos["symbol"]] = {
                        "quantity": int(pos["quantity"]),
                        "avg_price": float(pos["average_price"]),
                        "ltp": float(pos["ltp"]),
                        "pnl": float(pos["pnl"])
                    }

            logger.info(f"Open positions: {len(positions)}")

            return {
                "positions": positions,
                "count": len(positions)
            }

        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return {"error": str(e)}

    def update_daily_pnl(self) -> float:
        """
        更新并返回当日盈亏

        Returns:
            当日盈亏
        """
        try:
            response = self.client.positionbook()

            if response.get("status") != "success":
                return 0.0

            positions = response.get("data", [])
            total_pnl = sum(float(pos.get("pnl", 0)) for pos in positions)

            return total_pnl

        except Exception as e:
            logger.error(f"Error updating P&L: {e}")
            return 0.0

    def shutdown(self):
        """关闭线程池"""
        self.executor.shutdown(wait=True)
        logger.info("Market data service shutdown")
