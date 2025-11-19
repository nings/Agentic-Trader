"""测试OrderExecutor订单执行服务"""

import pytest
from unittest.mock import Mock, patch
from agentic_trader.services import OrderExecutor
from agentic_trader.core import TradeState


class TestOrderExecutor:
    """OrderExecutor测试套件"""

    @pytest.fixture
    def order_executor(self, mock_openalgo_client, trade_state):
        """创建OrderExecutor实例"""
        return OrderExecutor(
            client=mock_openalgo_client,
            state=trade_state,
            exchange="NSE",
            product="MIS"
        )

    def test_initialization(self, order_executor):
        """测试初始化"""
        assert order_executor.exchange == "NSE"
        assert order_executor.product == "MIS"
        assert order_executor.state is not None

    def test_place_market_order_success(self, order_executor, mock_openalgo_client, trade_state):
        """测试下单（成功）"""
        # Mock下单响应
        mock_openalgo_client.placeorder.return_value = {
            "status": "success",
            "orderid": "123456"
        }

        result = order_executor.place_market_order(
            symbol="ICICIBANK",
            action="BUY",
            quantity=7,
            reason="Test order"
        )

        assert result["success"] is True
        assert result["order_id"] == "123456"
        assert result["symbol"] == "ICICIBANK"
        assert result["action"] == "BUY"
        assert result["quantity"] == 7

        # 验证状态更新
        assert trade_state.get_trade_count("ICICIBANK") == 1
        assert len(trade_state.trade_history) == 1

    def test_place_market_order_failure(self, order_executor, mock_openalgo_client):
        """测试下单（失败）"""
        mock_openalgo_client.placeorder.return_value = {
            "status": "error",
            "message": "Insufficient funds"
        }

        result = order_executor.place_market_order(
            symbol="ICICIBANK",
            action="BUY",
            quantity=7,
            reason="Test order"
        )

        assert result["success"] is False
        assert "error" in result
        assert "Insufficient funds" in result["error"]

    def test_place_market_order_invalid_quantity(self, order_executor):
        """测试下单（无效数量）"""
        result = order_executor.place_market_order(
            symbol="ICICIBANK",
            action="BUY",
            quantity=0,
            reason="Test order"
        )

        assert result["success"] is False
        assert "Invalid quantity" in result["error"]

        result2 = order_executor.place_market_order(
            symbol="ICICIBANK",
            action="BUY",
            quantity=-5,
            reason="Test order"
        )

        assert result2["success"] is False

    def test_place_market_order_exception(self, order_executor, mock_openalgo_client):
        """测试下单（异常）"""
        mock_openalgo_client.placeorder.side_effect = Exception("Network error")

        result = order_executor.place_market_order(
            symbol="ICICIBANK",
            action="BUY",
            quantity=7,
            reason="Test order"
        )

        assert result["success"] is False
        assert "error" in result

    @patch('time.sleep')  # Mock sleep以加快测试
    def test_place_bulk_orders_success(self, mock_sleep, order_executor, mock_openalgo_client):
        """测试批量下单（成功）"""
        mock_openalgo_client.placeorder.return_value = {
            "status": "success",
            "orderid": "123456"
        }

        orders = [
            {"symbol": "ICICIBANK", "action": "BUY", "quantity": 7, "reason": "Test 1"},
            {"symbol": "RELIANCE", "action": "SELL", "quantity": 5, "reason": "Test 2"}
        ]

        result = order_executor.place_bulk_orders(orders)

        assert result["success"] is True
        assert result["total_orders"] == 2
        assert result["successful"] == 2
        assert len(result["results"]) == 2

    def test_place_bulk_orders_empty(self, order_executor):
        """测试批量下单（空列表）"""
        result = order_executor.place_bulk_orders([])

        assert result["success"] is True
        assert result["total_orders"] == 0
        assert result["successful"] == 0

    @patch('time.sleep')
    def test_place_bulk_orders_mixed_results(self, mock_sleep, order_executor, mock_openalgo_client):
        """测试批量下单（混合结果）"""
        # 第一个成功，第二个失败
        mock_openalgo_client.placeorder.side_effect = [
            {"status": "success", "orderid": "123456"},
            {"status": "error", "message": "Insufficient funds"}
        ]

        orders = [
            {"symbol": "ICICIBANK", "action": "BUY", "quantity": 7, "reason": "Test 1"},
            {"symbol": "RELIANCE", "action": "SELL", "quantity": 5, "reason": "Test 2"}
        ]

        result = order_executor.place_bulk_orders(orders)

        assert result["success"] is True
        assert result["total_orders"] == 2
        assert result["successful"] == 1

    def test_square_off_all_positions_success(self, order_executor, mock_openalgo_client):
        """测试平仓所有持仓（成功）"""
        # Mock持仓响应
        mock_openalgo_client.positionbook.return_value = {
            "status": "success",
            "data": [
                {
                    "symbol": "ICICIBANK",
                    "quantity": "10",
                    "exchange": "NSE",
                    "product": "MIS"
                },
                {
                    "symbol": "RELIANCE",
                    "quantity": "-5",  # 空头持仓
                    "exchange": "NSE",
                    "product": "MIS"
                },
                {
                    "symbol": "WIPRO",
                    "quantity": "0",  # 无仓位
                    "exchange": "NSE",
                    "product": "MIS"
                }
            ]
        }

        # Mock平仓下单响应
        mock_openalgo_client.placeorder.return_value = {
            "status": "success",
            "orderid": "CLOSE123"
        }

        result = order_executor.square_off_all_positions()

        assert result["success"] is True
        assert result["closed_count"] == 2  # ICICIBANK和RELIANCE
        assert result["failed_count"] == 0
        assert len(result["closed_positions"]) == 2

        # 验证第一个平仓（多头→卖出）
        first_close = result["closed_positions"][0]
        assert first_close["symbol"] == "ICICIBANK"
        assert first_close["action"] == "SELL"

        # 验证第二个平仓（空头→买入）
        second_close = result["closed_positions"][1]
        assert second_close["symbol"] == "RELIANCE"
        assert second_close["action"] == "BUY"

    def test_square_off_all_positions_no_positions(self, order_executor, mock_openalgo_client):
        """测试平仓（无持仓）"""
        mock_openalgo_client.positionbook.return_value = {
            "status": "success",
            "data": []
        }

        result = order_executor.square_off_all_positions()

        assert result["success"] is True
        assert result["closed_count"] == 0

    def test_square_off_all_positions_get_positions_failed(self, order_executor, mock_openalgo_client):
        """测试平仓（获取持仓失败）"""
        mock_openalgo_client.positionbook.return_value = {
            "status": "error",
            "message": "API error"
        }

        result = order_executor.square_off_all_positions()

        assert result["success"] is False
        assert "error" in result

    def test_square_off_all_positions_order_failed(self, order_executor, mock_openalgo_client):
        """测试平仓（部分下单失败）"""
        mock_openalgo_client.positionbook.return_value = {
            "status": "success",
            "data": [
                {
                    "symbol": "ICICIBANK",
                    "quantity": "10",
                    "exchange": "NSE",
                    "product": "MIS"
                }
            ]
        }

        # 平仓下单失败
        mock_openalgo_client.placeorder.return_value = {
            "status": "error",
            "message": "Order rejected"
        }

        result = order_executor.square_off_all_positions()

        assert result["success"] is True
        assert result["closed_count"] == 0
        assert result["failed_count"] == 1

    def test_square_off_all_positions_exception(self, order_executor, mock_openalgo_client):
        """测试平仓（异常）"""
        mock_openalgo_client.positionbook.side_effect = Exception("Network error")

        result = order_executor.square_off_all_positions()

        assert result["success"] is False
        assert "error" in result

    def test_cancel_all_pending_orders_success(self, order_executor, mock_openalgo_client, trade_state):
        """测试取消所有挂单（成功）"""
        mock_openalgo_client.cancelallorder.return_value = {
            "status": "success",
            "message": "All orders cancelled"
        }

        result = order_executor.cancel_all_pending_orders()

        assert result["success"] is True
        assert result["action"] == "cancel_orders"

        # 验证添加到历史
        assert len(trade_state.trade_history) == 1
        assert trade_state.trade_history[0]["action"] == "CANCEL_ALL_ORDERS"

    def test_cancel_all_pending_orders_exception(self, order_executor, mock_openalgo_client):
        """测试取消挂单（异常）"""
        mock_openalgo_client.cancelallorder.side_effect = Exception("API error")

        result = order_executor.cancel_all_pending_orders()

        assert result["success"] is False
        assert "error" in result

    def test_state_update_after_orders(self, order_executor, mock_openalgo_client, trade_state):
        """测试下单后状态更新"""
        mock_openalgo_client.placeorder.return_value = {
            "status": "success",
            "orderid": "123456"
        }

        # 下3单
        order_executor.place_market_order("ICICIBANK", "BUY", 7, "Test 1")
        order_executor.place_market_order("ICICIBANK", "BUY", 5, "Test 2")
        order_executor.place_market_order("RELIANCE", "SELL", 3, "Test 3")

        # 验证交易计数
        assert trade_state.get_trade_count("ICICIBANK") == 2
        assert trade_state.get_trade_count("RELIANCE") == 1

        # 验证历史记录
        assert len(trade_state.trade_history) == 3
