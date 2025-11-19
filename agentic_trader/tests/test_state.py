"""测试TradeState状态管理"""

import pytest
import json
from pathlib import Path
from agentic_trader.core import TradeState


class TestTradeState:
    """TradeState测试套件"""

    def test_initialization(self):
        """测试初始化"""
        state = TradeState()

        assert state.daily_pnl == 0.0
        assert state.trade_counts == {}
        assert state.trade_history == []
        assert state.stop_loss_hit is False
        assert state.squared_off_today is False

    def test_update_pnl(self, trade_state):
        """测试盈亏更新"""
        trade_state.update_pnl(-500.0)
        assert trade_state.daily_pnl == -500.0

        trade_state.update_pnl(300.0)
        assert trade_state.daily_pnl == 300.0

    def test_increment_trade_count(self, trade_state):
        """测试交易计数"""
        trade_state.increment_trade_count("ICICIBANK")
        assert trade_state.get_trade_count("ICICIBANK") == 1

        trade_state.increment_trade_count("ICICIBANK")
        assert trade_state.get_trade_count("ICICIBANK") == 2

        trade_state.increment_trade_count("RELIANCE")
        assert trade_state.get_trade_count("RELIANCE") == 1
        assert trade_state.get_trade_count("ICICIBANK") == 2

    def test_get_trade_count_nonexistent(self, trade_state):
        """测试获取不存在的交易计数"""
        assert trade_state.get_trade_count("UNKNOWN") == 0

    def test_add_trade_history(self, trade_state):
        """测试添加交易历史"""
        trade = {
            "symbol": "ICICIBANK",
            "action": "BUY",
            "quantity": 7,
            "order_id": "123"
        }

        trade_state.add_trade_history(trade)

        assert len(trade_state.trade_history) == 1
        assert trade_state.trade_history[0]["symbol"] == "ICICIBANK"
        assert trade_state.trade_history[0]["action"] == "BUY"
        assert "timestamp" in trade_state.trade_history[0]

    def test_set_stop_loss_hit(self, trade_state):
        """测试设置止损触发"""
        assert trade_state.stop_loss_hit is False

        trade_state.set_stop_loss_hit(True)
        assert trade_state.stop_loss_hit is True

        trade_state.set_stop_loss_hit(False)
        assert trade_state.stop_loss_hit is False

    def test_set_squared_off_today(self, trade_state):
        """测试设置平仓状态"""
        assert trade_state.squared_off_today is False

        trade_state.set_squared_off_today(True)
        assert trade_state.squared_off_today is True

    def test_reset_daily_state(self, trade_state):
        """测试重置每日状态"""
        # 设置一些数据
        trade_state.update_pnl(-500.0)
        trade_state.increment_trade_count("ICICIBANK")
        trade_state.set_stop_loss_hit(True)
        trade_state.set_squared_off_today(True)

        # 重置
        trade_state.reset_daily_state()

        # 验证重置
        assert trade_state.daily_pnl == 0.0
        assert trade_state.trade_counts == {}
        assert trade_state.stop_loss_hit is False
        assert trade_state.squared_off_today is False

    def test_to_dict(self, trade_state):
        """测试序列化为字典"""
        trade_state.update_pnl(-500.0)
        trade_state.increment_trade_count("ICICIBANK")
        trade_state.add_trade_history({"symbol": "ICICIBANK", "action": "BUY"})

        data = trade_state.to_dict()

        assert data["daily_pnl"] == -500.0
        assert data["trade_counts"]["ICICIBANK"] == 1
        assert data["total_trades"] == 1
        assert data["stop_loss_hit"] is False

    def test_from_dict(self):
        """测试从字典反序列化"""
        data = {
            "daily_pnl": -500.0,
            "trade_counts": {"ICICIBANK": 2},
            "stop_loss_hit": True,
            "squared_off_today": False
        }

        state = TradeState.from_dict(data)

        assert state.daily_pnl == -500.0
        assert state.trade_counts["ICICIBANK"] == 2
        assert state.stop_loss_hit is True
        assert state.squared_off_today is False

    def test_thread_safety(self, trade_state):
        """测试线程安全（基本检查）"""
        import threading

        def update_pnl():
            for _ in range(100):
                current = trade_state.daily_pnl
                trade_state.update_pnl(current - 1)

        threads = [threading.Thread(target=update_pnl) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 线程安全应该保证最终值是-1000
        assert trade_state.daily_pnl == -1000.0

    def test_repr(self, trade_state):
        """测试字符串表示"""
        trade_state.update_pnl(-500.0)
        trade_state.increment_trade_count("ICICIBANK")

        repr_str = repr(trade_state)

        assert "TradeState" in repr_str
        assert "pnl=-500.00" in repr_str
        assert "trades=1" in repr_str
        assert "stop_loss=False" in repr_str
