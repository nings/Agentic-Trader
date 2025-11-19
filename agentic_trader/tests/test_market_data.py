"""测试MarketDataService市场数据服务"""

import pytest
from unittest.mock import Mock, patch
from agentic_trader.services import MarketDataService


class TestMarketDataService:
    """MarketDataService测试套件"""

    @pytest.fixture
    def market_data_service(self, mock_openalgo_client):
        """创建MarketDataService实例"""
        return MarketDataService(
            client=mock_openalgo_client,
            symbols=["ICICIBANK", "RELIANCE"],
            exchange="NSE",
            max_workers=2
        )

    def test_initialization(self, market_data_service):
        """测试初始化"""
        assert market_data_service.symbols == ["ICICIBANK", "RELIANCE"]
        assert market_data_service.exchange == "NSE"
        assert market_data_service.executor is not None

    def test_fetch_quotes_success(self, market_data_service):
        """测试获取报价（成功）"""
        result = market_data_service.fetch_quotes("ICICIBANK")

        assert result["symbol"] == "ICICIBANK"
        assert result["ltp"] == 1350.50
        assert result["volume"] == 1000000
        assert "open" in result
        assert "high" in result
        assert "low" in result

    def test_fetch_quotes_failure(self, market_data_service, mock_openalgo_client):
        """测试获取报价（失败）"""
        # 设置Mock返回错误
        mock_openalgo_client.quotes.return_value = {
            "status": "error",
            "message": "Invalid symbol"
        }

        with pytest.raises(ValueError, match="Failed to fetch quotes"):
            market_data_service.fetch_quotes("INVALID")

    def test_fetch_depth_success(self, market_data_service):
        """测试获取深度（成功）"""
        result = market_data_service.fetch_depth("ICICIBANK")

        assert result["symbol"] == "ICICIBANK"
        assert "bid_ask_ratio" in result
        assert "total_bid_qty" in result
        assert "total_ask_qty" in result
        assert result["bid_ask_ratio"] == 2.0  # 100 / 50

    def test_fetch_depth_failure(self, market_data_service, mock_openalgo_client):
        """测试获取深度（失败）"""
        mock_openalgo_client.depth.return_value = {
            "status": "error",
            "message": "Invalid symbol"
        }

        with pytest.raises(ValueError, match="Failed to fetch depth"):
            market_data_service.fetch_depth("INVALID")

    def test_fetch_depth_zero_asks(self, market_data_service, mock_openalgo_client):
        """测试获取深度（卖单为0）"""
        mock_openalgo_client.depth.return_value = {
            "status": "success",
            "data": {
                "bids": [{"price": 1350.00, "quantity": 100}],
                "asks": []  # 空卖单
            }
        }

        result = market_data_service.fetch_depth("ICICIBANK")

        assert result["bid_ask_ratio"] == 0  # 卖单为0时比率应为0
        assert result["total_ask_qty"] == 0

    @patch('time.sleep')  # Mock sleep以加快测试
    def test_fetch_all_market_data(self, mock_sleep, market_data_service, mock_openalgo_client):
        """测试并发获取所有市场数据"""
        # Mock IndicatorCalculator
        with patch('agentic_trader.services.market_data.IndicatorCalculator') as MockCalc:
            mock_calc_instance = MockCalc.return_value
            mock_calc_instance.calculate_all.return_value = {
                "current": {
                    "rsi": 55.0,
                    "macd_trend": "bullish",
                    "ema_trend": "bullish"
                }
            }

            result = market_data_service.fetch_all_market_data(timeout=30)

            assert result["status"] == "success"
            assert "data" in result
            assert len(result["data"]) == 2
            assert "ICICIBANK" in result["data"]
            assert "RELIANCE" in result["data"]
            assert "elapsed_seconds" in result

    @patch('time.sleep')
    def test_fetch_symbol_data_with_delay(self, mock_sleep, market_data_service):
        """测试单个股票数据获取（带延迟）"""
        with patch('agentic_trader.services.market_data.IndicatorCalculator') as MockCalc:
            mock_calc_instance = MockCalc.return_value
            mock_calc_instance.calculate_all.return_value = {
                "current": {
                    "rsi": 55.0,
                    "macd_trend": "bullish",
                    "ema_trend": "bullish"
                }
            }

            result = market_data_service._fetch_symbol_data_with_delay("ICICIBANK", 0)

            assert result["symbol"] == "ICICIBANK"
            assert result["ltp"] == 1350.50
            assert result["volume"] == 1000000
            assert result["rsi"] == 55.0

    @patch('time.sleep')
    def test_fetch_symbol_data_error_handling(self, mock_sleep, market_data_service, mock_openalgo_client):
        """测试单个股票数据获取错误处理"""
        # 设置quotes失败
        mock_openalgo_client.quotes.return_value = {
            "status": "error",
            "message": "API error"
        }

        result = market_data_service._fetch_symbol_data_with_delay("ICICIBANK", 0)

        assert "error" in result
        assert result["symbol"] == "ICICIBANK"

    def test_get_account_funds_success(self, market_data_service):
        """测试获取账户资金（成功）"""
        result = market_data_service.get_account_funds()

        assert result["available_cash"] == 100000.0
        assert "m2m_unrealized" in result
        assert "m2m_realized" in result

    def test_get_account_funds_failure(self, market_data_service, mock_openalgo_client):
        """测试获取账户资金（失败）"""
        mock_openalgo_client.funds.return_value = {
            "status": "error",
            "message": "API error"
        }

        result = market_data_service.get_account_funds()

        assert "error" in result

    def test_get_positions_success(self, market_data_service, mock_openalgo_client):
        """测试获取持仓（成功）"""
        mock_openalgo_client.positionbook.return_value = {
            "status": "success",
            "data": [
                {
                    "symbol": "ICICIBANK",
                    "quantity": "10",
                    "average_price": "1340.00",
                    "ltp": "1350.50",
                    "pnl": "105.00"
                },
                {
                    "symbol": "RELIANCE",
                    "quantity": "0",  # 应该被过滤
                    "average_price": "0",
                    "ltp": "0",
                    "pnl": "0"
                }
            ]
        }

        result = market_data_service.get_positions()

        assert result["count"] == 1
        assert "ICICIBANK" in result["positions"]
        assert "RELIANCE" not in result["positions"]
        assert result["positions"]["ICICIBANK"]["quantity"] == 10
        assert result["positions"]["ICICIBANK"]["pnl"] == 105.00

    def test_get_positions_failure(self, market_data_service, mock_openalgo_client):
        """测试获取持仓（失败）"""
        mock_openalgo_client.positionbook.return_value = {
            "status": "error",
            "message": "API error"
        }

        result = market_data_service.get_positions()

        assert "error" in result

    def test_update_daily_pnl(self, market_data_service, mock_openalgo_client):
        """测试更新当日盈亏"""
        mock_openalgo_client.positionbook.return_value = {
            "status": "success",
            "data": [
                {"pnl": "105.00"},
                {"pnl": "250.50"},
                {"pnl": "-50.00"}
            ]
        }

        total_pnl = market_data_service.update_daily_pnl()

        assert total_pnl == 305.50

    def test_update_daily_pnl_error(self, market_data_service, mock_openalgo_client):
        """测试更新当日盈亏（错误）"""
        mock_openalgo_client.positionbook.return_value = {
            "status": "error"
        }

        total_pnl = market_data_service.update_daily_pnl()

        assert total_pnl == 0.0

    def test_shutdown(self, market_data_service):
        """测试关闭服务"""
        market_data_service.shutdown()

        # 验证线程池已关闭（无法再提交任务）
        with pytest.raises(RuntimeError):
            market_data_service.executor.submit(lambda: None)
