"""测试IndicatorCalculator技术指标服务"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch
from agentic_trader.services import IndicatorCalculator


class TestIndicatorCalculator:
    """IndicatorCalculator测试套件"""

    @pytest.fixture
    def indicator_calculator(self, mock_openalgo_client):
        """创建IndicatorCalculator实例"""
        return IndicatorCalculator(
            client=mock_openalgo_client,
            symbol="ICICIBANK",
            exchange="NSE"
        )

    @pytest.fixture
    def sample_historical_data(self):
        """生成示例历史数据"""
        dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='5min')

        # 生成模拟价格数据
        close_prices = 1350 + np.cumsum(np.random.randn(100) * 2)
        high_prices = close_prices + np.random.rand(100) * 5
        low_prices = close_prices - np.random.rand(100) * 5
        open_prices = close_prices + np.random.randn(100) * 2
        volume = np.random.randint(10000, 50000, 100)

        df = pd.DataFrame({
            'timestamp': dates,
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': volume
        })

        return df

    def test_initialization(self, indicator_calculator):
        """测试初始化"""
        assert indicator_calculator.symbol == "ICICIBANK"
        assert indicator_calculator.exchange == "NSE"

    def test_calculate_all_with_data(self, indicator_calculator, mock_openalgo_client, sample_historical_data):
        """测试计算所有指标（有数据）"""
        # Mock历史数据响应
        mock_openalgo_client.history.return_value = sample_historical_data

        result = indicator_calculator.calculate_all(lookback_bars=5)

        assert result["symbol"] == "ICICIBANK"
        assert result["lookback_bars"] == 5
        assert "current" in result
        assert "bars" in result

        # 验证当前指标
        current = result["current"]
        assert "rsi" in current
        assert "macd" in current
        assert "macd_trend" in current
        assert "ema_trend" in current
        assert "price" in current

        # 验证K线数据
        bars = result["bars"]
        assert len(bars["close"]) <= 5
        assert len(bars["rsi"]) <= 5

    def test_calculate_all_no_data(self, indicator_calculator, mock_openalgo_client):
        """测试计算指标（无数据）"""
        # Mock返回错误
        mock_openalgo_client.history.return_value = {
            "status": "error",
            "message": "No data available"
        }

        result = indicator_calculator.calculate_all()

        # 应该返回默认指标
        assert result["current"]["rsi"] == 50.0
        assert result["current"]["rsi_signal"] == "neutral"
        assert result["current"]["macd_trend"] == "neutral"

    def test_calculate_all_exception(self, indicator_calculator, mock_openalgo_client):
        """测试计算指标（异常）"""
        mock_openalgo_client.history.side_effect = Exception("Network error")

        result = indicator_calculator.calculate_all()

        # 应该返回默认指标
        assert result["current"]["rsi"] == 50.0

    def test_calculate_rsi(self, indicator_calculator):
        """测试RSI计算"""
        # 创建测试数据
        close_prices = np.array([100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 110] * 5)

        rsi = indicator_calculator._calculate_rsi(close_prices)

        assert len(rsi) == len(close_prices)
        assert not np.isnan(rsi[-1])  # 最后一个值应该有效

    def test_calculate_macd(self, indicator_calculator):
        """测试MACD计算"""
        close_prices = np.array([100 + i * 0.5 for i in range(100)])

        macd_data = indicator_calculator._calculate_macd(close_prices)

        assert "macd" in macd_data
        assert "signal" in macd_data
        assert "histogram" in macd_data
        assert len(macd_data["macd"]) == len(close_prices)

    def test_calculate_bollinger_bands(self, indicator_calculator):
        """测试布林带计算"""
        close_prices = np.array([100 + np.sin(i/10) * 5 for i in range(100)])

        bb_data = indicator_calculator._calculate_bollinger_bands(close_prices)

        assert "upper" in bb_data
        assert "middle" in bb_data
        assert "lower" in bb_data

        # 验证上轨 > 中轨 > 下轨
        valid_idx = ~np.isnan(bb_data["upper"])
        if valid_idx.any():
            assert np.all(bb_data["upper"][valid_idx] >= bb_data["middle"][valid_idx])
            assert np.all(bb_data["middle"][valid_idx] >= bb_data["lower"][valid_idx])

    def test_calculate_ema(self, indicator_calculator):
        """测试EMA计算"""
        close_prices = np.array([100 + i * 0.5 for i in range(100)])

        ema_data = indicator_calculator._calculate_ema(close_prices)

        assert "ema_20" in ema_data
        assert "ema_50" in ema_data
        assert len(ema_data["ema_20"]) == len(close_prices)

    def test_calculate_atr(self, indicator_calculator):
        """测试ATR计算"""
        n = 50
        high = np.array([105 + i * 0.5 for i in range(n)])
        low = np.array([95 + i * 0.5 for i in range(n)])
        close = np.array([100 + i * 0.5 for i in range(n)])

        atr = indicator_calculator._calculate_atr(high, low, close)

        assert len(atr) == n
        assert not np.isnan(atr[-1])

    def test_calculate_stochastic(self, indicator_calculator):
        """测试随机指标计算"""
        n = 50
        high = np.array([105 + i * 0.5 for i in range(n)])
        low = np.array([95 + i * 0.5 for i in range(n)])
        close = np.array([100 + i * 0.5 for i in range(n)])

        stoch_data = indicator_calculator._calculate_stochastic(high, low, close)

        assert "slowk" in stoch_data
        assert "slowd" in stoch_data
        assert len(stoch_data["slowk"]) == n

    def test_calculate_adx(self, indicator_calculator):
        """测试ADX计算"""
        n = 50
        high = np.array([105 + i * 0.5 for i in range(n)])
        low = np.array([95 + i * 0.5 for i in range(n)])
        close = np.array([100 + i * 0.5 for i in range(n)])

        adx = indicator_calculator._calculate_adx(high, low, close)

        assert len(adx) == n

    def test_rsi_signal_interpretation(self, indicator_calculator, mock_openalgo_client, sample_historical_data):
        """测试RSI信号解读"""
        mock_openalgo_client.history.return_value = sample_historical_data

        result = indicator_calculator.calculate_all()

        rsi_signal = result["current"]["rsi_signal"]
        rsi_value = result["current"]["rsi"]

        if rsi_value > 70:
            assert rsi_signal == "overbought"
        elif rsi_value < 30:
            assert rsi_signal == "oversold"
        else:
            assert rsi_signal == "neutral"

    def test_macd_trend_interpretation(self, indicator_calculator, mock_openalgo_client, sample_historical_data):
        """测试MACD趋势解读"""
        mock_openalgo_client.history.return_value = sample_historical_data

        result = indicator_calculator.calculate_all()

        macd = result["current"]["macd"]
        macd_signal = result["current"]["macd_signal"]
        macd_trend = result["current"]["macd_trend"]

        if macd > macd_signal:
            assert macd_trend == "bullish"
        else:
            assert macd_trend == "bearish"

    def test_ema_trend_interpretation(self, indicator_calculator, mock_openalgo_client, sample_historical_data):
        """测试EMA趋势解读"""
        mock_openalgo_client.history.return_value = sample_historical_data

        result = indicator_calculator.calculate_all()

        ema_20 = result["current"]["ema_20"]
        ema_50 = result["current"]["ema_50"]
        ema_trend = result["current"]["ema_trend"]

        if ema_20 > ema_50:
            assert ema_trend == "bullish"
        else:
            assert ema_trend == "bearish"

    def test_default_indicators_structure(self, indicator_calculator):
        """测试默认指标结构"""
        defaults = indicator_calculator._get_default_indicators()

        assert defaults["symbol"] == "ICICIBANK"
        assert defaults["lookback_bars"] == 0
        assert defaults["current"]["rsi"] == 50.0
        assert defaults["current"]["rsi_signal"] == "neutral"
        assert defaults["current"]["macd_trend"] == "neutral"
        assert defaults["current"]["ema_trend"] == "neutral"
        assert defaults["volatility_1h"] == 0.0
        assert defaults["avg_volume_1h"] == 0

    def test_extract_last_n_bars(self, indicator_calculator, sample_historical_data):
        """测试提取最近N个K线"""
        close_prices = sample_historical_data['close'].values
        high_prices = sample_historical_data['high'].values
        low_prices = sample_historical_data['low'].values

        # 计算指标
        rsi = indicator_calculator._calculate_rsi(close_prices)
        macd_data = indicator_calculator._calculate_macd(close_prices)
        bb_data = indicator_calculator._calculate_bollinger_bands(close_prices)
        ema_data = indicator_calculator._calculate_ema(close_prices)
        atr = indicator_calculator._calculate_atr(high_prices, low_prices, close_prices)
        stoch_data = indicator_calculator._calculate_stochastic(high_prices, low_prices, close_prices)
        adx = indicator_calculator._calculate_adx(high_prices, low_prices, close_prices)

        # 提取最近5个K线
        result = indicator_calculator._extract_last_n_bars(
            close_prices, rsi, macd_data, bb_data,
            ema_data, atr, stoch_data, adx, 5
        )

        assert result["lookback_bars"] == 5
        assert "current" in result
        assert "bars" in result
        assert len(result["bars"]["close"]) == 5

    def test_volatility_and_volume_calculation(self, indicator_calculator, mock_openalgo_client, sample_historical_data):
        """测试波动率和成交量计算"""
        mock_openalgo_client.history.return_value = sample_historical_data

        result = indicator_calculator.calculate_all()

        assert "volatility_1h" in result
        assert "avg_volume_1h" in result
        assert result["volatility_1h"] >= 0
        assert result["avg_volume_1h"] >= 0

    def test_trend_strength_interpretation(self, indicator_calculator, mock_openalgo_client, sample_historical_data):
        """测试趋势强度解读"""
        mock_openalgo_client.history.return_value = sample_historical_data

        result = indicator_calculator.calculate_all()

        adx = result["current"]["adx"]
        trend_strength = result["current"]["trend_strength"]

        if adx > 25:
            assert trend_strength == "strong"
        else:
            assert trend_strength == "weak"
