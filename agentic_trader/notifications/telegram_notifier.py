"""Telegram通知器"""

import logging
import requests
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """
    Telegram消息通知器

    发送交易告警和报告到Telegram
    """

    def __init__(self, bot_token: str, chat_id: str):
        """
        初始化Telegram通知器

        Args:
            bot_token: Telegram Bot Token
            chat_id: Telegram Chat ID
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

        logger.info("TelegramNotifier initialized")

    def send_message(
        self,
        message: str,
        parse_mode: str = "HTML",
        disable_notification: bool = False
    ) -> Dict[str, Any]:
        """
        发送文本消息

        Args:
            message: 消息内容
            parse_mode: 解析模式（HTML/Markdown）
            disable_notification: 是否静默发送

        Returns:
            API响应
        """
        url = f"{self.base_url}/sendMessage"

        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": parse_mode,
            "disable_notification": disable_notification
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()

            logger.info(f"Telegram message sent successfully")

            return {
                "success": True,
                "response": response.json()
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Telegram message: {e}")

            return {
                "success": False,
                "error": str(e)
            }

    def send_alert(
        self,
        severity: str,
        message: str,
        timestamp: Optional[str] = None
    ):
        """
        发送告警消息

        Args:
            severity: 严重程度
            message: 告警消息
            timestamp: 时间戳
        """
        # 根据严重程度选择emoji
        emoji_map = {
            "critical": "🚨",
            "warning": "⚠️",
            "info": "ℹ️",
            "success": "✅"
        }

        emoji = emoji_map.get(severity.lower(), "📢")

        # 格式化消息
        formatted_message = f"""
{emoji} <b>{severity.upper()} ALERT</b>

{message}

<i>Time: {timestamp or 'N/A'}</i>
        """

        # 重要告警不静音
        disable_notification = severity.lower() not in ["critical", "warning"]

        return self.send_message(
            formatted_message,
            disable_notification=disable_notification
        )

    def send_daily_report(
        self,
        metrics: Dict[str, Any]
    ):
        """
        发送每日报告

        Args:
            metrics: 指标字典
        """
        daily_pnl = metrics.get('daily_pnl', 0)
        total_trades = metrics.get('total_trades', 0)
        win_rate = metrics.get('win_rate', 0)

        # 根据盈亏选择emoji
        pnl_emoji = "🟢" if daily_pnl > 0 else "🔴" if daily_pnl < 0 else "⚪"

        message = f"""
📊 <b>Daily Trading Report</b>

{pnl_emoji} <b>P&L:</b> Rs.{daily_pnl:,.2f}
📈 <b>Total Trades:</b> {total_trades}
🎯 <b>Win Rate:</b> {win_rate:.1%}

<b>Positions:</b> {metrics.get('current_positions', 0)}
💰 <b>Cash Available:</b> Rs.{metrics.get('cash_available', 0):,.2f}
📊 <b>Portfolio Value:</b> Rs.{metrics.get('portfolio_value', 0):,.2f}

<i>Generated: {metrics.get('timestamp', 'N/A')}</i>
        """

        return self.send_message(message, disable_notification=True)

    def send_trade_notification(
        self,
        symbol: str,
        action: str,
        quantity: int,
        price: float,
        reason: str
    ):
        """
        发送交易通知

        Args:
            symbol: 股票代码
            action: 交易动作
            quantity: 数量
            price: 价格
            reason: 原因
        """
        action_emoji = "🟢" if action == "BUY" else "🔴"

        message = f"""
{action_emoji} <b>Trade Executed</b>

<b>Symbol:</b> {symbol}
<b>Action:</b> {action}
<b>Quantity:</b> {quantity}
<b>Price:</b> Rs.{price:.2f}

<b>Reason:</b> {reason}
        """

        return self.send_message(message, disable_notification=True)

    def test_connection(self) -> bool:
        """
        测试Telegram连接

        Returns:
            是否连接成功
        """
        result = self.send_message("✅ Telegram connection test successful!")
        return result.get("success", False)
