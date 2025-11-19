"""测试RiskManager风险管理"""

import pytest
from datetime import datetime
from agentic_trader.services import RiskManager
from agentic_trader.core import TradeState


class TestRiskManager:
    """RiskManager测试套件"""

    @pytest.fixture
    def risk_manager(self, mock_openalgo_client, trade_state):
        """创建RiskManager实例"""
        return RiskManager(
            client=mock_openalgo_client,
            state=trade_state,
            max_trades_per_symbol=5,
            daily_stop_loss=-10000.0
        )

    def test_initialization(self, risk_manager):
        """测试初始化"""
        assert risk_manager.max_trades_per_symbol == 5
        assert risk_manager.daily_stop_loss == -10000.0

    def test_check_constraints_pass(self, risk_manager):
        """测试风险检查通过"""
        result = risk_manager.check_constraints("ICICIBANK", "BUY")

        assert result["allowed"] is True
        assert "passed" in result["reason"].lower()

    def test_check_constraints_stop_loss_hit(self, risk_manager, trade_state):
        """测试止损触发"""
        trade_state.set_stop_loss_hit(True)

        result = risk_manager.check_constraints("ICICIBANK", "BUY")

        assert result["allowed"] is False
        assert "loss limit" in result["reason"].lower()

    def test_check_constraints_stop_loss_threshold(self, risk_manager, trade_state):
        """测试达到止损阈值"""
        trade_state.update_pnl(-10500.0)

        result = risk_manager.check_constraints("ICICIBANK", "BUY")

        assert result["allowed"] is False
        assert "stop-loss" in result["reason"].lower()
        assert trade_state.stop_loss_hit is True

    def test_check_constraints_max_trades_reached(self, risk_manager, trade_state):
        """测试达到最大交易次数"""
        for _ in range(5):
            trade_state.increment_trade_count("ICICIBANK")

        result = risk_manager.check_constraints("ICICIBANK", "BUY")

        assert result["allowed"] is False
        assert "max trades" in result["reason"].lower()

    def test_calculate_position_size_valid(self, risk_manager):
        """测试仓位计算（有效）"""
        result = risk_manager.calculate_position_size(
            symbol="ICICIBANK",
            ltp=1350.50,
            max_investment=10000.0
        )

        assert result["success"] is True
        assert result["quantity"] == 7  # int(10000 / 1350.50)
        assert result["ltp"] == 1350.50
        assert result["actual_investment"] == 7 * 1350.50

    def test_calculate_position_size_invalid_ltp(self, risk_manager):
        """测试仓位计算（无效LTP）"""
        result = risk_manager.calculate_position_size(
            symbol="ICICIBANK",
            ltp=0.0,
            max_investment=10000.0
        )

        assert result["success"] is False
        assert "error" in result
        assert result["quantity"] == 0

    def test_calculate_position_size_high_price(self, risk_manager):
        """测试仓位计算（价格过高）"""
        result = risk_manager.calculate_position_size(
            symbol="ICICIBANK",
            ltp=15000.0,  # 高于max_investment
            max_investment=10000.0
        )

        assert result["success"] is False
        assert result["quantity"] == 0

    def test_calculate_multiple_positions(self, risk_manager):
        """测试批量仓位计算"""
        positions = [
            {"symbol": "ICICIBANK", "ltp": 1350.0, "max_investment": 10000.0},
            {"symbol": "RELIANCE", "ltp": 2450.0, "max_investment": 10000.0}
        ]

        results = risk_manager.calculate_multiple_positions(positions)

        assert len(results) == 2
        assert results[0]["symbol"] == "ICICIBANK"
        assert results[0]["quantity"] == 7
        assert results[1]["symbol"] == "RELIANCE"
        assert results[1]["quantity"] == 4

    def test_check_multiple_constraints(self, risk_manager):
        """测试批量风险检查"""
        trades = [
            {"symbol": "ICICIBANK", "action": "BUY"},
            {"symbol": "RELIANCE", "action": "SELL"}
        ]

        results = risk_manager.check_multiple_constraints(trades)

        assert len(results) == 2
        assert all(r["allowed"] for r in results)

    def test_check_multiple_constraints_mixed(self, risk_manager, trade_state):
        """测试批量风险检查（混合结果）"""
        # 设置ICICIBANK达到交易限制
        for _ in range(5):
            trade_state.increment_trade_count("ICICIBANK")

        trades = [
            {"symbol": "ICICIBANK", "action": "BUY"},
            {"symbol": "RELIANCE", "action": "SELL"}
        ]

        results = risk_manager.check_multiple_constraints(trades)

        assert len(results) == 2
        assert results[0]["allowed"] is False  # ICICIBANK达到限制
        assert results[1]["allowed"] is True   # RELIANCE正常
