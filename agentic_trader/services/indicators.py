"""技术指标计算服务"""

import logging
import numpy as np
import talib
from typing import Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class IndicatorCalculator:
    """
    技术指标计算器

    使用TA-Lib库计算各种技术指标
    """

    def __init__(self, client, symbol: str, exchange: str = "NSE"):
        """
        初始化指标计算器

        Args:
            client: OpenAlgo客户端
            symbol: 股票代码
            exchange: 交易所
        """
        self.client = client
        self.symbol = symbol
        self.exchange = exchange

    def calculate_all(self, lookback_bars: int = 5) -> Dict[str, Any]:
        """
        计算所有技术指标

        Args:
            lookback_bars: 返回的K线数量

        Returns:
            包含所有指标的字典
        """
        try:
            # 获取历史数据
            historical_data = self._fetch_historical_data()

            if historical_data is None:
                return self._get_default_indicators()

            # 提取价格数据
            close_prices = historical_data['close'].values
            high_prices = historical_data['high'].values
            low_prices = historical_data['low'].values
            volume = historical_data['volume'].values

            # 计算各项指标
            rsi_values = self._calculate_rsi(close_prices)
            macd_values = self._calculate_macd(close_prices)
            bb_values = self._calculate_bollinger_bands(close_prices)
            ema_values = self._calculate_ema(close_prices)
            atr_values = self._calculate_atr(high_prices, low_prices, close_prices)
            stoch_values = self._calculate_stochastic(high_prices, low_prices, close_prices)
            adx_values = self._calculate_adx(high_prices, low_prices, close_prices)

            # 提取最近N个K线的数据
            indicators = self._extract_last_n_bars(
                close_prices, rsi_values, macd_values, bb_values,
                ema_values, atr_values, stoch_values, adx_values,
                lookback_bars
            )

            # 计算额外指标
            recent_data = historical_data.tail(12)  # 最近1小时
            indicators["volatility_1h"] = round(recent_data['close'].std(), 2)
            indicators["avg_volume_1h"] = int(recent_data['volume'].mean())

            logger.debug(f"Calculated indicators for {self.symbol}: RSI={indicators['current']['rsi']}")

            return indicators

        except Exception as e:
            logger.error(f"Error calculating indicators for {self.symbol}: {e}")
            return self._get_default_indicators()

    def _fetch_historical_data(self):
        """获取历史数据"""
        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")

            response = self.client.history(
                symbol=self.symbol,
                exchange=self.exchange,
                interval="5m",
                start_date=start_date,
                end_date=end_date
            )

            if isinstance(response, dict) and response.get("status") == "error":
                logger.warning(f"Failed to fetch history for {self.symbol}: {response.get('message')}")
                return None

            return response

        except Exception as e:
            logger.error(f"Error fetching historical data for {self.symbol}: {e}")
            return None

    def _calculate_rsi(self, close_prices: np.ndarray, period: int = 14) -> np.ndarray:
        """计算RSI指标"""
        return talib.RSI(close_prices, timeperiod=period)

    def _calculate_macd(self, close_prices: np.ndarray) -> Dict[str, np.ndarray]:
        """计算MACD指标"""
        macd, macd_signal, macd_hist = talib.MACD(
            close_prices,
            fastperiod=12,
            slowperiod=26,
            signalperiod=9
        )
        return {
            "macd": macd,
            "signal": macd_signal,
            "histogram": macd_hist
        }

    def _calculate_bollinger_bands(self, close_prices: np.ndarray, period: int = 20) -> Dict[str, np.ndarray]:
        """计算布林带指标"""
        upper_band, middle_band, lower_band = talib.BBANDS(close_prices, timeperiod=period)
        return {
            "upper": upper_band,
            "middle": middle_band,
            "lower": lower_band
        }

    def _calculate_ema(self, close_prices: np.ndarray) -> Dict[str, np.ndarray]:
        """计算EMA指标"""
        return {
            "ema_20": talib.EMA(close_prices, timeperiod=20),
            "ema_50": talib.EMA(close_prices, timeperiod=50)
        }

    def _calculate_atr(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        """计算ATR指标（波动性）"""
        return talib.ATR(high, low, close, timeperiod=period)

    def _calculate_stochastic(self, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> Dict[str, np.ndarray]:
        """计算随机指标"""
        slowk, slowd = talib.STOCH(high, low, close)
        return {
            "slowk": slowk,
            "slowd": slowd
        }

    def _calculate_adx(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        """计算ADX指标（趋势强度）"""
        return talib.ADX(high, low, close, timeperiod=period)

    def _extract_last_n_bars(
        self,
        close_prices: np.ndarray,
        rsi: np.ndarray,
        macd_data: Dict,
        bb_data: Dict,
        ema_data: Dict,
        atr: np.ndarray,
        stoch_data: Dict,
        adx: np.ndarray,
        n: int
    ) -> Dict[str, Any]:
        """提取最近N个K线的指标数据"""

        def get_last_n_valid(arr: np.ndarray, n: int) -> List[float]:
            """获取最后N个有效值"""
            valid_arr = arr[~np.isnan(arr)]
            if len(valid_arr) == 0:
                return []
            return [round(float(x), 2) for x in valid_arr[-n:]]

        # 提取K线数据
        rsi_bars = get_last_n_valid(rsi, n)
        macd_bars = get_last_n_valid(macd_data["macd"], n)
        macd_signal_bars = get_last_n_valid(macd_data["signal"], n)
        macd_hist_bars = get_last_n_valid(macd_data["histogram"], n)
        bb_upper_bars = get_last_n_valid(bb_data["upper"], n)
        bb_middle_bars = get_last_n_valid(bb_data["middle"], n)
        bb_lower_bars = get_last_n_valid(bb_data["lower"], n)
        ema_20_bars = get_last_n_valid(ema_data["ema_20"], n)
        ema_50_bars = get_last_n_valid(ema_data["ema_50"], n)
        atr_bars = get_last_n_valid(atr, n)
        stoch_bars = get_last_n_valid(stoch_data["slowk"], n)
        adx_bars = get_last_n_valid(adx, n)
        close_bars = [round(float(x), 2) for x in close_prices[-n:]]

        # 当前值（最新K线）
        current_rsi = rsi_bars[-1] if rsi_bars else 50.0
        current_macd = macd_bars[-1] if macd_bars else 0.0
        current_macd_signal = macd_signal_bars[-1] if macd_signal_bars else 0.0
        current_price = close_bars[-1] if close_bars else 0.0
        current_ema_20 = ema_20_bars[-1] if ema_20_bars else current_price
        current_ema_50 = ema_50_bars[-1] if ema_50_bars else current_price
        current_atr = atr_bars[-1] if atr_bars else 0.0
        current_stoch = stoch_bars[-1] if stoch_bars else 50.0
        current_adx = adx_bars[-1] if adx_bars else 0.0

        # 信号解读
        rsi_signal = "overbought" if current_rsi > 70 else "oversold" if current_rsi < 30 else "neutral"
        macd_trend = "bullish" if current_macd > current_macd_signal else "bearish"
        bb_upper = bb_upper_bars[-1] if bb_upper_bars else current_price
        bb_lower = bb_lower_bars[-1] if bb_lower_bars else current_price
        bb_position = "overbought" if current_price > bb_upper else "oversold" if current_price < bb_lower else "neutral"
        ema_trend = "bullish" if current_ema_20 > current_ema_50 else "bearish"
        stoch_signal = "overbought" if current_stoch > 80 else "oversold" if current_stoch < 20 else "neutral"
        trend_strength = "strong" if current_adx > 25 else "weak"

        return {
            "symbol": self.symbol,
            "lookback_bars": n,
            "current": {
                "price": current_price,
                "rsi": current_rsi,
                "rsi_signal": rsi_signal,
                "macd": current_macd,
                "macd_signal": current_macd_signal,
                "macd_trend": macd_trend,
                "bb_position": bb_position,
                "ema_20": current_ema_20,
                "ema_50": current_ema_50,
                "ema_trend": ema_trend,
                "atr": current_atr,
                "stoch": current_stoch,
                "stoch_signal": stoch_signal,
                "adx": current_adx,
                "trend_strength": trend_strength,
            },
            "bars": {
                "close": close_bars,
                "rsi": rsi_bars,
                "macd": macd_bars,
                "macd_signal": macd_signal_bars,
                "macd_hist": macd_hist_bars,
                "bb_upper": bb_upper_bars,
                "bb_middle": bb_middle_bars,
                "bb_lower": bb_lower_bars,
                "ema_20": ema_20_bars,
                "ema_50": ema_50_bars,
                "atr": atr_bars,
                "stoch": stoch_bars,
                "adx": adx_bars,
            }
        }

    def _get_default_indicators(self) -> Dict[str, Any]:
        """返回默认指标（当数据不可用时）"""
        return {
            "symbol": self.symbol,
            "lookback_bars": 0,
            "current": {
                "price": 0.0,
                "rsi": 50.0,
                "rsi_signal": "neutral",
                "macd": 0.0,
                "macd_signal": 0.0,
                "macd_trend": "neutral",
                "bb_position": "neutral",
                "ema_20": 0.0,
                "ema_50": 0.0,
                "ema_trend": "neutral",
                "atr": 0.0,
                "stoch": 50.0,
                "stoch_signal": "neutral",
                "adx": 0.0,
                "trend_strength": "weak",
            },
            "bars": {},
            "volatility_1h": 0.0,
            "avg_volume_1h": 0
        }
