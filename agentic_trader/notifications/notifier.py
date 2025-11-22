"""通知管理器 - 统一管理所有通知渠道"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class NotificationManager:
    """
    通知管理器

    统一管理Telegram、邮件等多种通知渠道
    """

    def __init__(self):
        """初始化通知管理器"""
        self.notifiers = []
        self.enabled = True

    def add_notifier(self, notifier):
        """
        添加通知器

        Args:
            notifier: 通知器实例（需实现send_alert方法）
        """
        self.notifiers.append(notifier)
        logger.info(f"Added notifier: {type(notifier).__name__}")

    def send_alert(
        self,
        severity: str,
        message: str,
        timestamp: Optional[datetime] = None
    ):
        """
        发送告警到所有渠道

        Args:
            severity: 严重程度
            message: 告警消息
            timestamp: 时间戳
        """
        if not self.enabled:
            logger.debug("Notifications disabled, skipping alert")
            return

        timestamp = timestamp or datetime.now()
        timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')

        logger.info(f"Sending {severity} alert to {len(self.notifiers)} notifiers")

        results = []

        for notifier in self.notifiers:
            try:
                result = notifier.send_alert(severity, message, timestamp_str)
                results.append({
                    'notifier': type(notifier).__name__,
                    'success': result.get('success', False)
                })
            except Exception as e:
                logger.error(f"Error in notifier {type(notifier).__name__}: {e}")
                results.append({
                    'notifier': type(notifier).__name__,
                    'success': False,
                    'error': str(e)
                })

        return results

    def send_daily_report(
        self,
        metrics: Dict[str, Any],
        trade_details: Optional[List[Dict]] = None
    ):
        """
        发送每日报告

        Args:
            metrics: 指标字典
            trade_details: 交易详情
        """
        if not self.enabled:
            logger.debug("Notifications disabled, skipping daily report")
            return

        logger.info(f"Sending daily report to {len(self.notifiers)} notifiers")

        results = []

        for notifier in self.notifiers:
            try:
                # 检查notifier是否有send_daily_report方法
                if hasattr(notifier, 'send_daily_report'):
                    result = notifier.send_daily_report(metrics, trade_details)
                    results.append({
                        'notifier': type(notifier).__name__,
                        'success': result.get('success', False)
                    })
            except Exception as e:
                logger.error(f"Error in notifier {type(notifier).__name__}: {e}")
                results.append({
                    'notifier': type(notifier).__name__,
                    'success': False,
                    'error': str(e)
                })

        return results

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
        if not self.enabled:
            return

        for notifier in self.notifiers:
            try:
                if hasattr(notifier, 'send_trade_notification'):
                    notifier.send_trade_notification(
                        symbol, action, quantity, price, reason
                    )
            except Exception as e:
                logger.error(f"Error sending trade notification: {e}")

    def enable(self):
        """启用通知"""
        self.enabled = True
        logger.info("Notifications enabled")

    def disable(self):
        """禁用通知"""
        self.enabled = False
        logger.info("Notifications disabled")

    def test_all(self) -> Dict[str, bool]:
        """
        测试所有通知器连接

        Returns:
            测试结果字典
        """
        results = {}

        for notifier in self.notifiers:
            notifier_name = type(notifier).__name__

            try:
                if hasattr(notifier, 'test_connection'):
                    success = notifier.test_connection()
                    results[notifier_name] = success
                else:
                    results[notifier_name] = None  # 不支持测试
            except Exception as e:
                logger.error(f"Error testing {notifier_name}: {e}")
                results[notifier_name] = False

        return results
