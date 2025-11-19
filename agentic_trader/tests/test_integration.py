"""集成测试 - 测试完整交易流程"""

import pytest
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np

from agentic_trader.core import TradeState
from agentic_trader.services import (
    MarketDataService,
    RiskManager,
    OrderExecutor,
    IndicatorCalculator
)


class TestIntegration:
    """集成测试套件 - 测试完整交易流程"""

    @pytest.fixture
    def integrated_system(self, mock_openalgo_client, sample_historical_data):
        """创建集成系统"""
        # 创建状态管理
        state = TradeState()

        # 创建服务
        market_data_service = MarketDataService(
            client=mock_openalgo_client,
            symbols=["ICICIBANK", "RELIANCE"],
            exchange="NSE"
        )

        risk_manager = RiskManager(
            client=mock_openalgo_client,
            state=state,
            max_trades_per_symbol=3,
            daily_stop_loss=-5000.0
        )

        order_executor = OrderExecutor(
            client=mock_openalgo_client,
            state=state,
            exchange="NSE",
            product="MIS"
        )

        # Mock历史数据
        mock_openalgo_client.history.return_value = sample_historical_data

        return {
            "state": state,
            "market_data": market_data_service,
            "risk_manager": risk_manager,
            "order_executor": order_executor,
            "client": mock_openalgo_client
        }

    @pytest.fixture
    def sample_historical_data(self):
        """生成示例历史数据"""
        dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='5min')
        close_prices = 1350 + np.cumsum(np.random.randn(100) * 2)
        high_prices = close_prices + np.random.rand(100) * 5
        low_prices = close_prices - np.random.rand(100) * 5
        volume = np.random.randint(10000, 50000, 100)

        return pd.DataFrame({
            'timestamp': dates,
            'open': close_prices + np.random.randn(100) * 2,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': volume
        })

    @patch('time.sleep')  # 加速测试
    def test_full_trading_cycle_success(self, mock_sleep, integrated_system):
        """测试完整交易周期（成功流程）"""
        system = integrated_system
        client = system["client"]

        # Mock下单响应
        client.placeorder.return_value = {
            "status": "success",
            "orderid": "ORDER123"
        }

        # 1. 获取市场数据
        market_data = system["market_data"].fetch_all_market_data()

        assert market_data["status"] == "success"
        assert "ICICIBANK" in market_data["data"]

        # 2. 检查风险约束
        risk_check = system["risk_manager"].check_constraints("ICICIBANK", "BUY")

        assert risk_check["allowed"] is True

        # 3. 计算仓位
        position = system["risk_manager"].calculate_position_size(
            symbol="ICICIBANK",
            ltp=1350.0,
            max_investment=10000.0
        )

        assert position["success"] is True
        assert position["quantity"] > 0

        # 4. 下单
        order_result = system["order_executor"].place_market_order(
            symbol="ICICIBANK",
            action="BUY",
            quantity=position["quantity"],
            reason="Integration test trade"
        )

        assert order_result["success"] is True
        assert order_result["order_id"] == "ORDER123"

        # 5. 验证状态更新
        assert system["state"].get_trade_count("ICICIBANK") == 1
        assert len(system["state"].trade_history) == 1

    @patch('time.sleep')
    def test_trading_cycle_with_risk_rejection(self, mock_sleep, integrated_system):
        """测试交易周期（风险拒绝）"""
        system = integrated_system
        state = system["state"]

        # 设置止损触发
        state.set_stop_loss_hit(True)

        # 1. 获取市场数据（成功）
        market_data = system["market_data"].fetch_all_market_data()
        assert market_data["status"] == "success"

        # 2. 检查风险约束（应该被拒绝）
        risk_check = system["risk_manager"].check_constraints("ICICIBANK", "BUY")

        assert risk_check["allowed"] is False
        assert "loss limit" in risk_check["reason"].lower()

    @patch('time.sleep')
    def test_multiple_trades_max_limit(self, mock_sleep, integrated_system):
        """测试多次交易达到最大限制"""
        system = integrated_system
        client = system["client"]

        client.placeorder.return_value = {
            "status": "success",
            "orderid": "ORDER123"
        }

        # 下3单（达到限制）
        for i in range(3):
            risk_check = system["risk_manager"].check_constraints("ICICIBANK", "BUY")
            assert risk_check["allowed"] is True

            order_result = system["order_executor"].place_market_order(
                symbol="ICICIBANK",
                action="BUY",
                quantity=5,
                reason=f"Trade {i+1}"
            )
            assert order_result["success"] is True

        # 第4单应该被拒绝
        risk_check = system["risk_manager"].check_constraints("ICICIBANK", "BUY")
        assert risk_check["allowed"] is False
        assert "max trades" in risk_check["reason"].lower()

    @patch('time.sleep')
    def test_stop_loss_trigger_during_trading(self, mock_sleep, integrated_system):
        """测试交易中触发止损"""
        system = integrated_system
        state = system["state"]
        client = system["client"]

        client.placeorder.return_value = {
            "status": "success",
            "orderid": "ORDER123"
        }

        # 第1单成功
        risk_check = system["risk_manager"].check_constraints("ICICIBANK", "BUY")
        assert risk_check["allowed"] is True

        order_result = system["order_executor"].place_market_order(
            symbol="ICICIBANK",
            action="BUY",
            quantity=5,
            reason="Trade 1"
        )
        assert order_result["success"] is True

        # 模拟大额亏损
        state.update_pnl(-6000.0)

        # 第2单应该被止损拒绝
        risk_check = system["risk_manager"].check_constraints("RELIANCE", "BUY")
        assert risk_check["allowed"] is False
        assert state.stop_loss_hit is True

    @patch('time.sleep')
    def test_bulk_orders_with_mixed_risk_results(self, mock_sleep, integrated_system):
        """测试批量订单混合风险检查"""
        system = integrated_system
        state = system["state"]
        client = system["client"]

        client.placeorder.return_value = {
            "status": "success",
            "orderid": "ORDER123"
        }

        # 设置ICICIBANK达到交易限制
        for _ in range(3):
            state.increment_trade_count("ICICIBANK")

        # 批量风险检查
        trades = [
            {"symbol": "ICICIBANK", "action": "BUY"},
            {"symbol": "RELIANCE", "action": "SELL"}
        ]

        risk_results = system["risk_manager"].check_multiple_constraints(trades)

        assert len(risk_results) == 2
        assert risk_results[0]["allowed"] is False  # ICICIBANK达到限制
        assert risk_results[1]["allowed"] is True   # RELIANCE正常

        # 批量下单（只下RELIANCE）
        allowed_orders = [
            {"symbol": "RELIANCE", "action": "SELL", "quantity": 5, "reason": "Test"}
        ]

        bulk_result = system["order_executor"].place_bulk_orders(allowed_orders)

        assert bulk_result["success"] is True
        assert bulk_result["successful"] == 1

    @patch('time.sleep')
    def test_square_off_workflow(self, mock_sleep, integrated_system):
        """测试平仓工作流"""
        system = integrated_system
        client = system["client"]

        # Mock持仓
        client.positionbook.return_value = {
            "status": "success",
            "data": [
                {
                    "symbol": "ICICIBANK",
                    "quantity": "10",
                    "exchange": "NSE",
                    "product": "MIS",
                    "average_price": "1340.00",
                    "ltp": "1350.00",
                    "pnl": "100.00"
                }
            ]
        }

        # Mock平仓下单
        client.placeorder.return_value = {
            "status": "success",
            "orderid": "CLOSE123"
        }

        # 执行平仓
        result = system["order_executor"].square_off_all_positions()

        assert result["success"] is True
        assert result["closed_count"] == 1
        assert result["closed_positions"][0]["symbol"] == "ICICIBANK"

    @patch('time.sleep')
    def test_market_data_to_decision_workflow(self, mock_sleep, integrated_system, sample_historical_data):
        """测试从市场数据到交易决策的完整流程"""
        system = integrated_system
        client = system["client"]

        client.placeorder.return_value = {
            "status": "success",
            "orderid": "ORDER123"
        }

        # 1. 获取市场数据（包含技术指标）
        market_data = system["market_data"].fetch_all_market_data()

        assert market_data["status"] == "success"
        icici_data = market_data["data"]["ICICIBANK"]

        # 2. 根据市场数据和指标进行决策
        # 假设RSI < 40 且 MACD看涨 → BUY信号
        should_buy = (
            icici_data.get("rsi", 50) < 60 and
            icici_data.get("macd_trend") in ["bullish", "bearish", "neutral"]
        )

        if should_buy:
            # 3. 风险检查
            risk_check = system["risk_manager"].check_constraints("ICICIBANK", "BUY")

            if risk_check["allowed"]:
                # 4. 计算仓位
                position = system["risk_manager"].calculate_position_size(
                    symbol="ICICIBANK",
                    ltp=icici_data["ltp"],
                    max_investment=10000.0
                )

                if position["success"]:
                    # 5. 下单
                    order_result = system["order_executor"].place_market_order(
                        symbol="ICICIBANK",
                        action="BUY",
                        quantity=position["quantity"],
                        reason="RSI oversold + MACD bullish"
                    )

                    assert order_result["success"] is True

    @patch('time.sleep')
    def test_error_recovery_workflow(self, mock_sleep, integrated_system):
        """测试错误恢复流程"""
        system = integrated_system
        client = system["client"]

        # 第一次下单失败
        client.placeorder.return_value = {
            "status": "error",
            "message": "Temporary API error"
        }

        result1 = system["order_executor"].place_market_order(
            symbol="ICICIBANK",
            action="BUY",
            quantity=5,
            reason="Test"
        )

        assert result1["success"] is False

        # 第二次下单成功（模拟重试）
        client.placeorder.return_value = {
            "status": "success",
            "orderid": "ORDER123"
        }

        result2 = system["order_executor"].place_market_order(
            symbol="ICICIBANK",
            action="BUY",
            quantity=5,
            reason="Test retry"
        )

        assert result2["success"] is True

    def test_state_consistency_across_services(self, integrated_system):
        """测试服务间状态一致性"""
        system = integrated_system
        state = system["state"]
        client = system["client"]

        client.placeorder.return_value = {
            "status": "success",
            "orderid": "ORDER123"
        }

        # 通过OrderExecutor下单
        system["order_executor"].place_market_order(
            symbol="ICICIBANK",
            action="BUY",
            quantity=5,
            reason="Test"
        )

        # RiskManager应该看到相同的状态
        assert system["risk_manager"].state.get_trade_count("ICICIBANK") == 1

        # 状态应该被正确共享
        assert state.get_trade_count("ICICIBANK") == 1

    @patch('time.sleep')
    def test_concurrent_market_data_fetch(self, mock_sleep, integrated_system):
        """测试并发市场数据获取"""
        system = integrated_system

        # 获取多个股票的市场数据
        result = system["market_data"].fetch_all_market_data()

        assert result["status"] == "success"
        assert len(result["data"]) == 2
        assert "ICICIBANK" in result["data"]
        assert "RELIANCE" in result["data"]
        assert result["elapsed_seconds"] >= 0
