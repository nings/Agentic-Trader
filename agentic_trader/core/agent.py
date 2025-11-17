"""AI交易代理定义"""

import logging
from agents.agent import Agent
from agents.extensions.models.litellm_model import LitellmModel
from ..config import settings
from ..tools import (
    # Market tools
    get_all_market_data,
    get_market_quotes,
    get_market_depth,
    get_account_snapshot,
    get_current_positions,
    # Risk tools
    check_risk_constraints,
    check_all_risk_constraints,
    calculate_position_size,
    calculate_all_position_sizes,
    # Order tools
    place_market_order,
    place_bulk_orders,
    square_off_all_positions,
    cancel_all_pending_orders,
)

logger = logging.getLogger(__name__)


def create_trading_model():
    """
    创建AI模型实例

    Returns:
        LitellmModel实例
    """
    provider = settings.model_provider.value

    if provider == "cerebras":
        model_name = settings.cerebras_model
        api_key = settings.cerebras_api_key
        logger.info(f"Using Cerebras model: {model_name}")
    elif provider == "groq":
        model_name = settings.groq_model
        api_key = settings.groq_api_key
        logger.info(f"Using Groq model: {model_name}")
    elif provider == "custom":
        model_name = settings.custom_model
        api_key = settings.custom_api_key
        logger.info(f"Using custom model: {model_name}")
    else:  # openai
        model_name = settings.openai_model
        api_key = settings.openai_api_key
        logger.info(f"Using OpenAI model: {model_name}")

    return LitellmModel(model=model_name, api_key=api_key)


def create_trading_agent():
    """
    创建AI交易代理

    Returns:
        Agent实例
    """
    model = create_trading_model()

    agent = Agent(
        name="🎯 Autonomous Trading Agent",
        instructions="""Process 5 symbols. Plain text. NO MARKDOWN.

STEP 1: get_all_market_data() ONCE → all data for all 5 symbols
STEP 2: For each symbol, decide BUY/SELL/HOLD (RSI, MACD, EMA signals)
STEP 3: For each trade decision:
  - check_risk_constraints(symbol, action)
  - calculate_position_size(symbol, ltp)
  - Add to orders list if allowed
STEP 4: place_bulk_orders() ONCE with complete JSON array

CRITICAL: Keep reasons SHORT (2-4 words)

OUTPUT FORMAT (plain text, one line per symbol):
ICICIBANK: BUY Order#123 (MACD bullish)
RELIANCE: HOLD (weak signals)
SBIN: HOLD (existing position)
WIPRO: SELL Order#124 (take profit)
ITC: HOLD (mixed signals)""",
        tools=[
            # Bulk operations (FAST - use these)
            get_all_market_data,
            check_all_risk_constraints,
            calculate_all_position_sizes,
            place_bulk_orders,
            # Account tools
            get_account_snapshot,
            get_current_positions,
            # Legacy individual tools (fallback only - avoid)
            check_risk_constraints,
            calculate_position_size,
            place_market_order,
            get_market_quotes,
            get_market_depth,
            # Market control
            square_off_all_positions,
            cancel_all_pending_orders,
        ],
        model=model
    )

    logger.info("Trading agent created successfully")
    return agent
