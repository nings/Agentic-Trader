"""交易监控器 - 实时监控交易系统状态"""

import logging
import threading
import time
from typing import Dict, List, Callable, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class MonitorMetrics:
    """监控指标"""
    timestamp: datetime
    daily_pnl: float
    total_trades: int
    win_rate: float
    avg_profit: float
    avg_loss: float
    current_positions: int
    cash_available: float
    portfolio_value: float
    var_95: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    condition: Callable[[MonitorMetrics], bool]
    message_template: str
    severity: str  # 'info', 'warning', 'critical'
    cooldown_minutes: int = 30
    last_triggered: Optional[datetime] = None


class TradingMonitor:
    """
    交易监控器

    实时监控交易系统状态，触发告警
    """

    def __init__(
        self,
        state,
        check_interval: int = 60,  # 检查间隔（秒）
        alert_handlers: Optional[List[Callable]] = None
    ):
        """
        初始化监控器

        Args:
            state: 交易状态对象
            check_interval: 检查间隔（秒）
            alert_handlers: 告警处理器列表
        """
        self.state = state
        self.check_interval = check_interval
        self.alert_handlers = alert_handlers or []

        self.is_running = False
        self.monitor_thread = None

        # 告警规则
        self.alert_rules: List[AlertRule] = []
        self._setup_default_rules()

        # 历史指标
        self.metrics_history: deque = deque(maxlen=1000)

        logger.info("TradingMonitor initialized")

    def _setup_default_rules(self):
        """设置默认告警规则"""

        # 1. 止损触发
        self.add_alert_rule(
            name="stop_loss_triggered",
            condition=lambda m: self.state.stop_loss_hit,
            message_template="⛔ Stop loss triggered! Daily P&L: Rs.{daily_pnl:,.2f}",
            severity="critical",
            cooldown_minutes=60
        )

        # 2. 大额亏损
        self.add_alert_rule(
            name="large_loss",
            condition=lambda m: m.daily_pnl < -5000,
            message_template="⚠️ Large loss detected: Rs.{daily_pnl:,.2f}",
            severity="warning",
            cooldown_minutes=30
        )

        # 3. 大额盈利
        self.add_alert_rule(
            name="large_profit",
            condition=lambda m: m.daily_pnl > 10000,
            message_template="🎉 Large profit achieved: Rs.{daily_pnl:,.2f}",
            severity="info",
            cooldown_minutes=60
        )

        # 4. 交易次数过多
        self.add_alert_rule(
            name="excessive_trading",
            condition=lambda m: m.total_trades > 50,
            message_template="⚠️ Excessive trading detected: {total_trades} trades today",
            severity="warning",
            cooldown_minutes=120
        )

        # 5. 低胜率
        self.add_alert_rule(
            name="low_win_rate",
            condition=lambda m: m.total_trades > 10 and m.win_rate < 0.3,
            message_template="📉 Low win rate: {win_rate:.1%} ({total_trades} trades)",
            severity="warning",
            cooldown_minutes=120
        )

    def add_alert_rule(
        self,
        name: str,
        condition: Callable[[MonitorMetrics], bool],
        message_template: str,
        severity: str = "info",
        cooldown_minutes: int = 30
    ):
        """
        添加告警规则

        Args:
            name: 规则名称
            condition: 条件函数
            message_template: 消息模板
            severity: 严重程度
            cooldown_minutes: 冷却时间（分钟）
        """
        rule = AlertRule(
            name=name,
            condition=condition,
            message_template=message_template,
            severity=severity,
            cooldown_minutes=cooldown_minutes
        )

        self.alert_rules.append(rule)
        logger.info(f"Added alert rule: {name}")

    def add_alert_handler(self, handler: Callable):
        """
        添加告警处理器

        Args:
            handler: 处理器函数 (severity, message) -> None
        """
        self.alert_handlers.append(handler)

    def start(self):
        """启动监控"""
        if self.is_running:
            logger.warning("Monitor already running")
            return

        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

        logger.info("TradingMonitor started")

    def stop(self):
        """停止监控"""
        self.is_running = False

        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        logger.info("TradingMonitor stopped")

    def _monitor_loop(self):
        """监控循环"""
        while self.is_running:
            try:
                # 收集指标
                metrics = self._collect_metrics()

                # 保存到历史
                self.metrics_history.append(metrics)

                # 检查告警规则
                self._check_alert_rules(metrics)

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")

            # 等待下一次检查
            time.sleep(self.check_interval)

    def _collect_metrics(self) -> MonitorMetrics:
        """
        收集当前指标

        Returns:
            监控指标
        """
        # 从状态中获取数据
        daily_pnl = self.state.daily_pnl
        total_trades = sum(self.state.trade_counts.values())

        # 计算胜率
        trade_history = self.state.trade_history
        if trade_history:
            winning_trades = sum(
                1 for trade in trade_history
                if trade.get('pnl', 0) > 0
            )
            win_rate = winning_trades / len(trade_history) if trade_history else 0.0

            # 计算平均盈利和亏损
            profits = [t.get('pnl', 0) for t in trade_history if t.get('pnl', 0) > 0]
            losses = [t.get('pnl', 0) for t in trade_history if t.get('pnl', 0) < 0]

            avg_profit = sum(profits) / len(profits) if profits else 0.0
            avg_loss = sum(losses) / len(losses) if losses else 0.0
        else:
            win_rate = 0.0
            avg_profit = 0.0
            avg_loss = 0.0

        # 当前持仓数（假设从state获取）
        current_positions = len([
            symbol for symbol, count in self.state.trade_counts.items()
            if count > 0
        ])

        metrics = MonitorMetrics(
            timestamp=datetime.now(),
            daily_pnl=daily_pnl,
            total_trades=total_trades,
            win_rate=win_rate,
            avg_profit=avg_profit,
            avg_loss=avg_loss,
            current_positions=current_positions,
            cash_available=0.0,  # 需要从其他地方获取
            portfolio_value=0.0  # 需要从其他地方获取
        )

        return metrics

    def _check_alert_rules(self, metrics: MonitorMetrics):
        """
        检查告警规则

        Args:
            metrics: 当前指标
        """
        now = datetime.now()

        for rule in self.alert_rules:
            try:
                # 检查条件
                if not rule.condition(metrics):
                    continue

                # 检查冷却时间
                if rule.last_triggered:
                    cooldown_delta = timedelta(minutes=rule.cooldown_minutes)
                    if now - rule.last_triggered < cooldown_delta:
                        continue

                # 触发告警
                message = rule.message_template.format(**metrics.__dict__)

                self._trigger_alert(rule.severity, message, rule.name)

                # 更新触发时间
                rule.last_triggered = now

            except Exception as e:
                logger.error(f"Error checking rule {rule.name}: {e}")

    def _trigger_alert(self, severity: str, message: str, rule_name: str):
        """
        触发告警

        Args:
            severity: 严重程度
            message: 告警消息
            rule_name: 规则名称
        """
        logger.warning(f"ALERT [{severity.upper()}] {rule_name}: {message}")

        # 调用所有告警处理器
        for handler in self.alert_handlers:
            try:
                handler(severity, message)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")

    def get_current_metrics(self) -> MonitorMetrics:
        """获取当前指标"""
        return self._collect_metrics()

    def get_metrics_history(self, minutes: int = 60) -> List[MonitorMetrics]:
        """
        获取历史指标

        Args:
            minutes: 过去多少分钟

        Returns:
            指标列表
        """
        cutoff_time = datetime.now() - timedelta(minutes=minutes)

        return [
            m for m in self.metrics_history
            if m.timestamp >= cutoff_time
        ]

    def get_summary(self) -> Dict[str, Any]:
        """
        获取监控摘要

        Returns:
            摘要字典
        """
        metrics = self.get_current_metrics()

        return {
            'current_metrics': metrics,
            'alert_rules_count': len(self.alert_rules),
            'metrics_history_size': len(self.metrics_history),
            'is_running': self.is_running,
            'check_interval': self.check_interval
        }


class PerformanceTracker:
    """
    性能追踪器

    追踪系统性能指标（延迟、吞吐量等）
    """

    def __init__(self):
        """初始化性能追踪器"""
        self.api_latencies: deque = deque(maxlen=1000)
        self.order_execution_times: deque = deque(maxlen=1000)
        self.error_counts: Dict[str, int] = {}

    def record_api_latency(self, endpoint: str, latency_ms: float):
        """
        记录API延迟

        Args:
            endpoint: API端点
            latency_ms: 延迟（毫秒）
        """
        self.api_latencies.append({
            'endpoint': endpoint,
            'latency_ms': latency_ms,
            'timestamp': datetime.now()
        })

    def record_order_execution_time(self, symbol: str, execution_time_ms: float):
        """
        记录订单执行时间

        Args:
            symbol: 股票代码
            execution_time_ms: 执行时间（毫秒）
        """
        self.order_execution_times.append({
            'symbol': symbol,
            'execution_time_ms': execution_time_ms,
            'timestamp': datetime.now()
        })

    def record_error(self, error_type: str):
        """
        记录错误

        Args:
            error_type: 错误类型
        """
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

    def get_performance_summary(self) -> Dict[str, Any]:
        """
        获取性能摘要

        Returns:
            性能摘要
        """
        # API延迟统计
        if self.api_latencies:
            latencies = [r['latency_ms'] for r in self.api_latencies]
            api_stats = {
                'mean': sum(latencies) / len(latencies),
                'min': min(latencies),
                'max': max(latencies),
                'p50': sorted(latencies)[len(latencies) // 2],
                'p95': sorted(latencies)[int(len(latencies) * 0.95)],
                'p99': sorted(latencies)[int(len(latencies) * 0.99)]
            }
        else:
            api_stats = {}

        # 订单执行时间统计
        if self.order_execution_times:
            exec_times = [r['execution_time_ms'] for r in self.order_execution_times]
            exec_stats = {
                'mean': sum(exec_times) / len(exec_times),
                'min': min(exec_times),
                'max': max(exec_times),
                'p95': sorted(exec_times)[int(len(exec_times) * 0.95)]
            }
        else:
            exec_stats = {}

        return {
            'api_latency_stats': api_stats,
            'order_execution_stats': exec_stats,
            'error_counts': self.error_counts,
            'total_api_calls': len(self.api_latencies),
            'total_orders': len(self.order_execution_times)
        }
