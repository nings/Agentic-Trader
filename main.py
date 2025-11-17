"""
Agentic Trader v2.0 - 主程序入口

重构后的模块化架构版本
"""

import asyncio
import sys
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz
from openalgo import api
from agents.run import Runner

# 导入配置
from agentic_trader.config import settings
from agentic_trader.utils import setup_logging
from agentic_trader.core import TradeState, create_trading_agent
from agentic_trader.services import MarketDataService, RiskManager, OrderExecutor
from agentic_trader import tools

import logging

# 时区
IST = pytz.timezone('Asia/Kolkata')

# 全局对象
state = None
market_data_service = None
risk_manager = None
order_executor = None
trading_agent = None
client = None


def initialize_logging():
    """初始化日志系统"""
    setup_logging(
        log_level=settings.log_level,
        log_dir=settings.log_dir,
        enable_console=True,
        enable_structured=settings.enable_structured_logging
    )
    logger = logging.getLogger(__name__)
    logger.info("="*80)
    logger.info(f"Agentic Trader v2.0 - Environment: {settings.environment.value}")
    logger.info("="*80)


def initialize_openalgo_client():
    """初始化OpenAlgo客户端"""
    global client
    logger = logging.getLogger(__name__)

    try:
        client = api(
            api_key=settings.openalgo_api_key,
            host=settings.openalgo_host
        )
        logger.info(f"✓ OpenAlgo client initialized: {settings.openalgo_host}")
        return client
    except Exception as e:
        logger.error(f"✗ Failed to initialize OpenAlgo client: {e}")
        sys.exit(1)


def initialize_services():
    """初始化所有服务"""
    global state, market_data_service, risk_manager, order_executor
    logger = logging.getLogger(__name__)

    logger.info("Initializing services...")

    # 1. 创建交易状态管理器
    state = TradeState()
    logger.info("✓ Trade state initialized")

    # 2. 创建市场数据服务
    market_data_service = MarketDataService(
        client=client,
        symbols=settings.symbols,
        exchange=settings.exchange,
        max_workers=settings.max_concurrent_requests
    )
    logger.info("✓ Market data service initialized")

    # 3. 创建风险管理器
    risk_manager = RiskManager(
        client=client,
        state=state,
        max_trades_per_symbol=settings.max_trades_per_symbol,
        daily_stop_loss=settings.daily_stop_loss,
        square_off_hour=settings.square_off_hour,
        square_off_minute=settings.square_off_minute
    )
    logger.info("✓ Risk manager initialized")

    # 4. 创建订单执行器
    order_executor = OrderExecutor(
        client=client,
        state=state,
        exchange=settings.exchange,
        product=settings.product
    )
    logger.info("✓ Order executor initialized")

    # 5. 设置工具层的服务实例
    tools.set_market_data_service(market_data_service)
    tools.set_risk_manager(risk_manager)
    tools.set_order_executor(order_executor)
    logger.info("✓ Tool functions configured")


async def initialize_trading_state():
    """初始化交易状态（获取当前账户信息）"""
    logger = logging.getLogger(__name__)

    logger.info("="*80)
    logger.info("Initializing trading state...")
    logger.info("="*80)

    try:
        # 1. 获取账户资金
        logger.info("Fetching account funds...")
        funds = market_data_service.get_account_funds()
        if "error" not in funds:
            logger.info(f"✓ Available Cash: Rs.{funds['available_cash']:,.2f}")
            logger.info(f"✓ M2M Realized: Rs.{funds['m2m_realized']:,.2f}")
            logger.info(f"✓ M2M Unrealized: Rs.{funds['m2m_unrealized']:,.2f}")

        # 2. 获取持仓
        logger.info("Fetching open positions...")
        positions = market_data_service.get_positions()
        if "error" not in positions:
            logger.info(f"✓ Open Positions: {positions['count']}")

            if positions['count'] > 0:
                for symbol, pos in positions['positions'].items():
                    pnl_color = "+" if pos['pnl'] >= 0 else "-"
                    logger.info(
                        f"  • {symbol}: Qty={pos['quantity']}, "
                        f"Avg={pos['avg_price']:.2f}, LTP={pos['ltp']:.2f}, "
                        f"P&L={pnl_color}Rs.{abs(pos['pnl']):.2f}"
                    )

        # 3. 计算当日盈亏
        logger.info("Calculating daily P&L...")
        current_pnl = market_data_service.update_daily_pnl()
        state.update_pnl(current_pnl)
        pnl_prefix = "+" if current_pnl >= 0 else ""
        logger.info(f"✓ Daily P&L: {pnl_prefix}Rs.{current_pnl:,.2f}")

        # 4. 检查止损状态
        if current_pnl <= settings.daily_stop_loss:
            state.set_stop_loss_hit(True)
            logger.warning(f"⚠️ STOP-LOSS HIT! Trading will be blocked.")
        else:
            logger.info(f"✓ Stop-loss check: OK (limit: Rs.{settings.daily_stop_loss:,})")

        logger.info("="*80)
        logger.info("✓ Initialization complete")
        logger.info("="*80)

    except Exception as e:
        logger.error(f"✗ Initialization failed: {e}")
        import traceback
        traceback.print_exc()


async def run_trading_cycle():
    """执行一次交易周期"""
    logger = logging.getLogger(__name__)
    now = datetime.now(IST)

    logger.info("="*80)
    logger.info(f"Trading Cycle: {now.strftime('%Y-%m-%d %H:%M:%S IST')}")
    logger.info("="*80)

    # 检查交易时间
    if now.hour < settings.market_open_hour or \
       (now.hour == settings.market_open_hour and now.minute < settings.market_open_minute):
        logger.info(f"Market not open yet. Trading starts at {settings.market_open_hour}:{settings.market_open_minute:02d} AM IST.")
        return

    if now.hour > settings.square_off_hour or \
       (now.hour == settings.square_off_hour and now.minute >= settings.square_off_minute):
        # 平仓时间
        if not state.squared_off_today:
            logger.info("Market Closing Time - Squaring Off All Positions")
            order_executor.square_off_all_positions()
            order_executor.cancel_all_pending_orders()
            state.set_squared_off_today(True)
            logger.info("✓ Square-off completed. No more trading today.")
        else:
            logger.info(f"Market closed. Trading resumes at {settings.market_open_hour}:{settings.market_open_minute:02d} AM IST tomorrow.")
        return

    logger.info("Starting autonomous trading workflow...")

    # 更新当日盈亏
    current_pnl = market_data_service.update_daily_pnl()
    state.update_pnl(current_pnl)
    logger.info(f"Current Daily P&L: Rs.{current_pnl:.2f}")

    # 构造查询
    query = f"""Trade cycle {now.strftime('%H:%M')}. Process all 5 symbols. P&L: Rs.{state.daily_pnl:.0f}. Stop-loss: {state.stop_loss_hit}."""

    logger.info("🎯 Executing AI trading agent...")

    try:
        final_result = await Runner.run(
            trading_agent,
            input=query,
            max_turns=60
        )

        # 打印Token使用统计
        if hasattr(final_result, 'context_wrapper') and hasattr(final_result.context_wrapper, 'usage'):
            usage = final_result.context_wrapper.usage
            logger.info("="*80)
            logger.info("[TOKEN USAGE] API Call Statistics:")
            logger.info(f"  Requests:      {usage.requests if hasattr(usage, 'requests') else 'N/A'}")
            logger.info(f"  Input Tokens:  {usage.input_tokens:,}")
            logger.info(f"  Output Tokens: {usage.output_tokens:,}")
            logger.info(f"  Total Tokens:  {usage.total_tokens:,}")

            # 计算成本
            input_tokens = usage.input_tokens
            output_tokens = usage.output_tokens

            if settings.model_provider.value == "cerebras":
                cost = (input_tokens * 0.60 / 1_000_000) + (output_tokens * 0.60 / 1_000_000)
            elif settings.model_provider.value == "groq":
                cost = (input_tokens + output_tokens) * 0.05 / 1_000_000
            else:  # OpenAI
                cost = (input_tokens * 0.15 / 1_000_000) + (output_tokens * 0.60 / 1_000_000)

            logger.info(f"  Est. Cost:     ${cost:.6f}")
            logger.info("="*80)

        logger.info(f"[RESULT] {final_result.final_output}")

    except Exception as e:
        logger.error(f"✗ Trading cycle failed: {e}")
        logger.info("Skipping this cycle, will retry in next scheduled run")
        return

    logger.info("="*80)
    logger.info("Trading cycle completed.")
    logger.info("="*80)


def reset_daily_state():
    """重置每日状态"""
    logger = logging.getLogger(__name__)

    logger.info("="*80)
    logger.info("End of Day - Resetting State")
    logger.info(f"Final Daily P&L: Rs.{state.daily_pnl:.2f}")
    logger.info(f"Total Trades: {sum(state.trade_counts.values())}")
    logger.info("="*80)

    # 保存今天的交易历史
    import json
    with open(f"logs/trade_history_{datetime.now(IST).strftime('%Y%m%d')}.json", "w") as f:
        json.dump(state.to_dict(), f, indent=2)

    # 重置状态
    state.reset_daily_state()


async def start_autonomous_agent():
    """启动自主交易代理"""
    global trading_agent
    logger = logging.getLogger(__name__)

    logger.info("="*80)
    logger.info("🤖 OpenAlgo Autonomous AI Trading Agent v2.0")
    logger.info("   Self-Learning System with Modular Architecture")
    logger.info("="*80)
    logger.info(f"\nTrading Universe: {', '.join(settings.symbols)}")
    logger.info(f"Max Investment/Trade: Rs.{settings.max_investment_per_trade:,}")
    logger.info(f"Daily Stop-Loss: Rs.{settings.daily_stop_loss:,}")
    logger.info(f"Max Trades Per Symbol: {settings.max_trades_per_symbol}")
    logger.info(f"Square-Off Time: {settings.square_off_hour}:{settings.square_off_minute:02d} PM IST")
    logger.info("="*80)

    # 初始化交易状态
    await initialize_trading_state()

    # 创建AI代理
    logger.info("Creating AI trading agent...")
    trading_agent = create_trading_agent()

    # 设置调度器
    scheduler = AsyncIOScheduler(timezone=IST)

    # 每5分钟运行一次（交易时段内）
    scheduler.add_job(
        run_trading_cycle,
        'cron',
        day_of_week='mon-fri',
        hour='9-15',
        minute=f'*/{settings.trading_interval_minutes}',
        id='trading_cycle'
    )

    # 每日重置
    scheduler.add_job(
        reset_daily_state,
        'cron',
        day_of_week='mon-fri',
        hour=settings.daily_reset_hour,
        minute=settings.daily_reset_minute,
        id='daily_reset'
    )

    scheduler.start()
    logger.info(f"✓ Scheduler started - Agent will run every {settings.trading_interval_minutes} minutes during market hours\n")

    # 立即运行一次（如果在交易时段内）
    now = datetime.now(IST)
    if settings.market_open_hour <= now.hour < settings.square_off_hour or \
       (now.hour == settings.square_off_hour and now.minute < settings.square_off_minute):
        logger.info("Running initial test cycle...\n")
        await run_trading_cycle()
    else:
        logger.info(f"Outside market hours ({settings.market_open_hour}:{settings.market_open_minute:02d} AM - {settings.square_off_hour}:{settings.square_off_minute:02d} PM). Waiting for next scheduled run.\n")

    # 保持运行
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("\n\nShutting down agent...")
        scheduler.shutdown()
        if market_data_service:
            market_data_service.shutdown()


def main():
    """主函数"""
    # 1. 初始化日志
    initialize_logging()

    # 2. 初始化OpenAlgo客户端
    initialize_openalgo_client()

    # 3. 初始化服务
    initialize_services()

    # 4. 启动异步事件循环
    asyncio.run(start_autonomous_agent())


if __name__ == "__main__":
    main()
