## 高级功能文档

本文档介绍Agentic Trader v2.0的高级功能模块。

---

## 目录

1. [机器学习价格预测](#1-机器学习价格预测)
2. [智能订单执行](#2-智能订单执行)
3. [高级风险管理](#3-高级风险管理)
4. [实时监控告警](#4-实时监控告警)

---

## 1. 机器学习价格预测

### 概述

使用机器学习模型预测短期价格走势，辅助交易决策。

### 功能模块

#### 1.1 特征工程 (`agentic_trader/ml/feature_engineering.py`)

**FeatureEngineer类**：从原始市场数据提取机器学习特征

**特征类别** （共70+个特征）：

- **价格特征**：价格变化、高低价差、开盘收盘价差等
- **技术指标**：RSI、MACD、布林带、ATR、ADX、CCI、Stochastic等
- **统计特征**：滚动均值、标准差、最小值、最大值、偏度、峰度
- **时间特征**：小时、分钟、星期、市场时段
- **成交量特征**：成交量变化、相对成交量、价量相关性
- **波动率特征**：历史波动率、Parkinson波动率
- **动量特征**：动量指标、ROC、Williams %R

**使用示例**：

```python
from agentic_trader.ml import FeatureEngineer
import pandas as pd

# 准备历史数据
data = pd.read_csv("ICICIBANK_5min.csv")

# 创建特征
engineer = FeatureEngineer()
features_df = engineer.create_features(data)

# 创建预测目标
target = engineer.create_target(features_df, horizon=1, target_type='direction')

print(f"Created {len(engineer.feature_columns)} features")
```

#### 1.2 价格预测器 (`agentic_trader/ml/predictor.py`)

**支持的模型**：

1. **XGBoost** - 梯度提升树（推荐，快速且准确）
2. **LightGBM** - 轻量级梯度提升
3. **LSTM** - 长短期记忆神经网络

**PricePredictor类**：

```python
from agentic_trader.ml import PricePredictor, FeatureEngineer
import pandas as pd

# 1. 准备数据
data = pd.read_csv("historical_data.csv")
engineer = FeatureEngineer()
features_df = engineer.create_features(data)

# 分离特征和目标
X = features_df[engineer.feature_columns]
y = engineer.create_target(features_df, horizon=1, target_type='return')

# 2. 初始化并训练模型
predictor = PricePredictor(model_type='xgboost')
results = predictor.train(X, y, validation_split=0.2)

print(f"Training Score: {results['train_score']:.3f}")
print(f"Validation Score: {results['val_score']:.3f}")

# 3. 预测
predictions = predictor.predict(X_new)

# 4. 预测方向（上涨/下跌）
direction = predictor.predict_direction(X_new)

# 5. 带置信度预测
predictions, confidence = predictor.predict_with_confidence(X_new)

# 6. 查看特征重要性
top_features = predictor.get_top_features(n=10)
for feature, importance in top_features:
    print(f"{feature}: {importance:.4f}")

# 7. 保存模型
predictor.save_model("models/price_predictor.pkl")
```

**集成预测器**：

```python
from agentic_trader.ml.predictor import EnsemblePredictor

# 创建多个模型
model1 = PricePredictor(model_type='xgboost')
model2 = PricePredictor(model_type='lightgbm')
model3 = PricePredictor(model_type='lstm')

# 训练模型...
model1.train(X_train, y_train)
model2.train(X_train, y_train)
model3.train(X_train, y_train)

# 创建集成
ensemble = EnsemblePredictor(
    models=[model1, model2, model3],
    weights=[0.4, 0.4, 0.2]  # 自定义权重
)

# 集成预测
ensemble_predictions = ensemble.predict(X_new)
ensemble_direction = ensemble.predict_direction(X_new)
```

---

## 2. 智能订单执行

### 概述

优化订单执行策略，减少市场冲击，提高成交质量。

### 2.1 TWAP执行 (`agentic_trader/execution/algos.py`)

**时间加权平均价格** - 在指定时间内均匀分割订单

```python
from agentic_trader.execution import TWAPExecutor

executor = TWAPExecutor(client, order_executor)

# 执行TWAP策略
result = executor.execute(
    symbol="ICICIBANK",
    action="BUY",
    total_quantity=100,          # 总数量
    duration_minutes=30,          # 30分钟内执行
    num_slices=10,                # 分成10片
    reason="Large order execution"
)

print(f"Executed: {result.executed_quantity}/{result.total_quantity}")
print(f"Avg Price: Rs.{result.avg_price:.2f}")
print(f"Total Cost: Rs.{result.total_cost:,.2f}")
```

**优势**：
- ✅ 减少市场冲击
- ✅ 平滑成交价格
- ✅ 适合大额订单

### 2.2 VWAP执行

**成交量加权平均价格** - 根据历史成交量分布调整执行节奏

```python
from agentic_trader.execution import VWAPExecutor

executor = VWAPExecutor(client, order_executor)

# 执行VWAP策略
result = executor.execute(
    symbol="RELIANCE",
    action="SELL",
    total_quantity=50,
    duration_minutes=60,
    reason="Follow volume pattern"
)
```

**特点**：
- 开盘和收盘时段执行更多
- 午间低谷执行较少
- 更贴近市场自然节奏

### 2.3 智能订单路由

**SmartRouter** - 根据市场条件自动选择最佳执行策略

```python
from agentic_trader.execution import SmartRouter

router = SmartRouter(client, order_executor)

# 智能路由自动选择策略
result = router.execute(
    symbol="SBIN",
    action="BUY",
    quantity=75,
    max_duration_minutes=30,
    urgency='normal',  # 'low', 'normal', 'high', 'urgent'
    reason="Smart execution"
)
```

**决策逻辑**：

| 紧急程度 | 订单大小 | 流动性 | 价差 | 策略选择 |
|---------|---------|--------|------|---------|
| Urgent | 任意 | 任意 | 任意 | 立即执行 |
| High | 小 | 高 | 低 | 立即执行 |
| High | 大 | 低 | 高 | TWAP |
| Normal | 小 | 高 | 低 | 立即执行 |
| Normal | 大 | 任意 | 高 | TWAP |
| Normal | 大 | 任意 | 低 | VWAP |
| Low | 任意 | 任意 | 任意 | VWAP |

---

## 3. 高级风险管理

### 概述

多维度风险控制，包括VaR、动态止损、投资组合风险分析。

### 3.1 VaR计算器 (`agentic_trader/risk/var_calculator.py`)

**风险价值（VaR）** - 在给定置信水平下的最大可能损失

**支持的方法**：

1. **历史模拟法** - 基于历史收益率分布
2. **参数法（方差-协方差法）** - 假设正态分布
3. **蒙特卡洛模拟法** - 随机模拟
4. **条件VaR（CVaR）** - 超过VaR的平均损失

```python
from agentic_trader.risk import VaRCalculator
import pandas as pd

# 准备收益率数据
returns = pd.Series([0.01, -0.02, 0.015, -0.01, 0.02])  # 示例
portfolio_value = 100000.0

# 创建VaR计算器
var_calc = VaRCalculator(confidence_level=0.95)

# 1. 历史模拟法
historical_var = var_calc.historical_var(returns, portfolio_value)
print(f"Historical VaR (95%): Rs.{historical_var['var_amount']:,.2f}")

# 2. 参数法
parametric_var = var_calc.parametric_var(returns, portfolio_value)
print(f"Parametric VaR (95%): Rs.{parametric_var['var_amount']:,.2f}")

# 3. 蒙特卡洛模拟
mc_var = var_calc.monte_carlo_var(returns, portfolio_value, num_simulations=10000)
print(f"Monte Carlo VaR (95%): Rs.{mc_var['var_amount']:,.2f}")

# 4. 条件VaR
cvar = var_calc.conditional_var(returns, portfolio_value)
print(f"CVaR (95%): Rs.{cvar['cvar_amount']:,.2f}")

# 5. 所有方法对比
all_results = var_calc.calculate_all_methods(returns, portfolio_value)
```

### 3.2 动态止损管理 (`agentic_trader/risk/stop_loss_manager.py`)

#### 动态止损

基于ATR或波动率自动调整止损位

```python
from agentic_trader.risk import DynamicStopLoss

# 创建动态止损管理器
stop_manager = DynamicStopLoss(
    default_stop_pct=0.02,  # 默认2%
    use_atr=True,
    atr_multiplier=2.0      # 2倍ATR
)

# 计算止损位
level = stop_manager.calculate_stop_loss(
    symbol="ICICIBANK",
    entry_price=1350.0,
    direction='long',
    atr=15.0,  # 当前ATR
    volatility=0.015  # 当前波动率
)

print(f"Entry: Rs.{level.entry_price:.2f}")
print(f"Stop: Rs.{level.stop_price:.2f}")
print(f"Stop %: {level.stop_pct*100:.2f}%")

# 检查止损
check_result = stop_manager.check_stop_loss("ICICIBANK", current_price=1320.0)
if check_result['triggered']:
    print(f"⚠️ Stop loss triggered!")
```

#### 追踪止损

根据有利价格移动自动调整止损

```python
from agentic_trader.risk import TrailingStop

# 创建追踪止损
trailing_stop = TrailingStop(
    trailing_pct=0.03,            # 3%追踪距离
    min_profit_to_activate=0.01    # 1%盈利后激活
)

# 初始化
trailing_stop.initialize_trailing_stop(
    symbol="RELIANCE",
    entry_price=2450.0,
    direction='long',
    initial_stop_price=2400.0
)

# 价格上涨时更新
update_result = trailing_stop.update_trailing_stop("RELIANCE", current_price=2500.0)
if update_result['updated']:
    print(f"Trailing stop updated: Rs.{update_result['new_stop']:.2f}")

# 检查是否触发
check_result = trailing_stop.check_trailing_stop("RELIANCE", current_price=2420.0)
if check_result['triggered']:
    print(f"Trailing stop triggered! P&L: {check_result['pnl_pct']*100:.2f}%")
```

### 3.3 投资组合风险分析 (`agentic_trader/risk/portfolio_risk.py`)

**PortfolioRiskAnalyzer** - 分析整体投资组合风险

```python
from agentic_trader.risk import PortfolioRiskAnalyzer
import pandas as pd

# 准备持仓数据
positions = {
    "ICICIBANK": {"quantity": 10, "price": 1350.0, "value": 13500.0},
    "RELIANCE": {"quantity": 5, "price": 2450.0, "value": 12250.0},
    "SBIN": {"quantity": 20, "price": 650.0, "value": 13000.0}
}

# 准备历史收益率
returns_history = {
    "ICICIBANK": pd.Series([0.01, -0.02, 0.015]),
    "RELIANCE": pd.Series([0.008, -0.015, 0.012]),
    "SBIN": pd.Series([0.012, -0.018, 0.01])
}

# 分析投资组合风险
analyzer = PortfolioRiskAnalyzer(risk_free_rate=0.04)
risk_metrics = analyzer.analyze(positions, returns_history)

print(f"Portfolio Value: Rs.{risk_metrics.total_value:,.2f}")
print(f"VaR (95%): Rs.{risk_metrics.var_95:,.2f}")
print(f"CVaR (95%): Rs.{risk_metrics.cvar_95:,.2f}")
print(f"Portfolio Volatility: {risk_metrics.portfolio_volatility*100:.2f}%")
print(f"Sharpe Ratio: {risk_metrics.sharpe_ratio:.2f}")
print(f"Max Drawdown: {risk_metrics.max_drawdown*100:.2f}%")

# 集中度风险
concentration = risk_metrics.concentration_risk
print(f"Herfindahl Index: {concentration['herfindahl_index']:.3f}")
print(f"Effective N Assets: {concentration['effective_n_assets']:.1f}")
print(f"Max Single Weight: {concentration['max_single_weight']*100:.1f}%")

# 分散化检查
diversification = analyzer.check_diversification(
    weights={"ICICIBANK": 0.35, "RELIANCE": 0.32, "SBIN": 0.33},
    correlation_matrix=risk_metrics.correlation_matrix,
    max_correlation=0.7,
    max_single_weight=0.4
)

if not diversification['is_diversified']:
    for warning in diversification['warnings']:
        print(f"⚠️ {warning['message']}")
```

---

## 4. 实时监控告警

### 概述

实时监控交易系统状态，智能告警，多渠道通知。

### 4.1 交易监控器 (`agentic_trader/monitoring/monitor.py`)

**TradingMonitor** - 实时监控交易系统

```python
from agentic_trader.monitoring import TradingMonitor
from agentic_trader.core import TradeState

# 创建状态和监控器
state = TradeState()
monitor = TradingMonitor(
    state=state,
    check_interval=60  # 每60秒检查一次
)

# 添加自定义告警规则
monitor.add_alert_rule(
    name="high_profit",
    condition=lambda m: m.daily_pnl > 5000,
    message_template="🎉 High profit: Rs.{daily_pnl:,.2f}",
    severity="info",
    cooldown_minutes=30
)

# 添加告警处理器
def print_alert(severity, message):
    print(f"[{severity.upper()}] {message}")

monitor.add_alert_handler(print_alert)

# 启动监控
monitor.start()

# 获取当前指标
metrics = monitor.get_current_metrics()
print(f"Daily P&L: Rs.{metrics.daily_pnl:,.2f}")
print(f"Win Rate: {metrics.win_rate:.1%}")

# 停止监控
# monitor.stop()
```

**默认告警规则**：

1. ⛔ **止损触发** - 触发止损时告警
2. ⚠️ **大额亏损** - 亏损超过Rs.5000
3. 🎉 **大额盈利** - 盈利超过Rs.10000
4. ⚠️ **交易次数过多** - 超过50笔交易
5. 📉 **低胜率** - 胜率低于30%

### 4.2 通知系统 (`agentic_trader/notifications/`)

#### Telegram通知

```python
from agentic_trader.notifications import TelegramNotifier

# 初始化Telegram通知器
telegram = TelegramNotifier(
    bot_token="YOUR_BOT_TOKEN",
    chat_id="YOUR_CHAT_ID"
)

# 测试连接
if telegram.test_connection():
    print("✅ Telegram connected")

# 发送告警
telegram.send_alert(
    severity="warning",
    message="Daily loss exceeds limit",
    timestamp="2025-01-15 14:30:00"
)

# 发送每日报告
telegram.send_daily_report({
    'daily_pnl': -1250.50,
    'total_trades': 15,
    'win_rate': 0.53,
    'current_positions': 3,
    'cash_available': 85000.0,
    'portfolio_value': 95000.0
})

# 发送交易通知
telegram.send_trade_notification(
    symbol="ICICIBANK",
    action="BUY",
    quantity=10,
    price=1350.50,
    reason="RSI oversold"
)
```

#### 邮件通知

```python
from agentic_trader.notifications import EmailNotifier

# 初始化邮件通知器
email = EmailNotifier(
    smtp_server="smtp.gmail.com",
    smtp_port=587,
    sender_email="your_email@gmail.com",
    sender_password="your_app_password",
    recipient_emails=["recipient@example.com"],
    use_tls=True
)

# 测试连接
if email.test_connection():
    print("✅ Email connected")

# 发送告警
email.send_alert(
    severity="critical",
    message="Stop loss triggered!",
    timestamp=datetime.now()
)

# 发送每日报告
email.send_daily_report(
    metrics={...},
    trade_details=[...]
)
```

#### 通知管理器

统一管理多个通知渠道

```python
from agentic_trader.notifications import NotificationManager, TelegramNotifier, EmailNotifier

# 创建管理器
notif_manager = NotificationManager()

# 添加多个通知器
notif_manager.add_notifier(telegram)
notif_manager.add_notifier(email)

# 发送到所有渠道
notif_manager.send_alert("warning", "Large loss detected!")
notif_manager.send_daily_report({...})

# 测试所有连接
test_results = notif_manager.test_all()
for notifier, success in test_results.items():
    print(f"{notifier}: {'✅' if success else '❌'}")

# 临时禁用通知
notif_manager.disable()
```

### 4.3 性能追踪器

```python
from agentic_trader.monitoring import PerformanceTracker

tracker = PerformanceTracker()

# 记录API延迟
tracker.record_api_latency("quotes", latency_ms=150.5)

# 记录订单执行时间
tracker.record_order_execution_time("ICICIBANK", execution_time_ms=320.8)

# 记录错误
tracker.record_error("api_timeout")

# 获取性能摘要
summary = tracker.get_performance_summary()
print(f"API Latency P95: {summary['api_latency_stats']['p95']:.1f}ms")
print(f"Order Execution Mean: {summary['order_execution_stats']['mean']:.1f}ms")
```

### 4.4 仪表板

```python
from agentic_trader.monitoring import DashboardServer

# 创建仪表板服务器
dashboard = DashboardServer(monitor, port=8080)

# 导出静态HTML
dashboard.export_html_dashboard("dashboard.html")

# 或启动Web服务器（需要安装flask）
# dashboard.start_flask_server()
# 访问: http://localhost:8080/api/dashboard
```

---

## 集成示例

### 完整交易系统

```python
from agentic_trader.core import TradeState
from agentic_trader.services import MarketDataService, RiskManager, OrderExecutor
from agentic_trader.ml import FeatureEngineer, PricePredictor
from agentic_trader.execution import SmartRouter
from agentic_trader.risk import DynamicStopLoss, VaRCalculator, PortfolioRiskAnalyzer
from agentic_trader.monitoring import TradingMonitor, PerformanceTracker
from agentic_trader.notifications import NotificationManager, TelegramNotifier

# 1. 初始化核心组件
state = TradeState()
market_data = MarketDataService(client, symbols=["ICICIBANK", "RELIANCE"])
risk_manager = RiskManager(client, state)
order_executor = OrderExecutor(client, state)

# 2. 初始化ML模型
feature_engineer = FeatureEngineer()
price_predictor = PricePredictor(model_type='xgboost')
# price_predictor.load_model("models/trained_model.pkl")

# 3. 初始化高级执行
smart_router = SmartRouter(client, order_executor)

# 4. 初始化风险管理
stop_loss_manager = DynamicStopLoss(use_atr=True)
var_calculator = VaRCalculator(confidence_level=0.95)
portfolio_analyzer = PortfolioRiskAnalyzer()

# 5. 初始化监控告警
monitor = TradingMonitor(state, check_interval=60)
notif_manager = NotificationManager()
notif_manager.add_notifier(TelegramNotifier(bot_token="...", chat_id="..."))

# 添加告警处理器
monitor.add_alert_handler(lambda sev, msg: notif_manager.send_alert(sev, msg))

# 6. 启动监控
monitor.start()

# 7. 交易循环
while trading_active:
    # 获取市场数据
    data = market_data.fetch_all_market_data()

    # ML预测
    features = feature_engineer.create_features(historical_data)
    predictions = price_predictor.predict(features)

    # 风险检查
    risk_check = risk_manager.check_constraints(symbol, "BUY")

    if risk_check['allowed'] and predictions[0] > 0:
        # 智能执行
        result = smart_router.execute(
            symbol=symbol,
            action="BUY",
            quantity=10,
            urgency='normal'
        )

        # 设置动态止损
        if result.success:
            stop_loss_manager.calculate_stop_loss(
                symbol=symbol,
                entry_price=result.avg_price,
                direction='long',
                atr=current_atr
            )

# 8. 结束时生成报告
metrics = monitor.get_current_metrics()
notif_manager.send_daily_report(metrics)
monitor.stop()
```

---

## 依赖安装

```bash
# 基础依赖
pip install numpy pandas scikit-learn

# 机器学习
pip install xgboost lightgbm
pip install tensorflow  # LSTM支持（可选）

# 技术指标
pip install TA-Lib

# 统计分析
pip install scipy

# 通知
pip install requests  # Telegram

# 可选：Web仪表板
pip install flask flask-cors

# 可选：GARCH波动率模型
pip install arch
```

---

## 最佳实践

### 1. ML模型训练

```python
# 使用足够的历史数据（至少3-6个月）
# 定期重新训练模型（每周或每月）
# 使用样本外数据测试
# 监控模型性能下降
```

### 2. 风险管理

```python
# 始终设置止损
# 监控投资组合VaR
# 避免过度集中
# 定期检查相关性
```

### 3. 订单执行

```python
# 大额订单使用TWAP/VWAP
# 根据市场流动性调整策略
# 监控执行成本
```

### 4. 监控告警

```python
# 设置合理的告警阈值
# 避免告警疲劳
# 定期查看性能指标
```

---

## 故障排除

### Q: ML模型预测不准确？

A:
1. 检查特征质量和数量
2. 增加训练数据量
3. 尝试不同的模型类型
4. 调整超参数
5. 检查是否有前瞻偏差

### Q: TWAP/VWAP执行失败？

A:
1. 检查订单大小是否合理
2. 确认市场流动性
3. 检查API限流
4. 查看执行日志

### Q: 告警太多或太少？

A:
1. 调整告警阈值
2. 修改cooldown时间
3. 添加/移除告警规则

---

## 参考资料

- [机器学习交易策略](https://www.quantstart.com)
- [算法交易执行](https://www.investopedia.com/terms/a/algorithmictrading.asp)
- [VaR风险管理](https://www.investopedia.com/terms/v/var.asp)

---

**版本**: v2.0
**更新时间**: 2025-01-15
