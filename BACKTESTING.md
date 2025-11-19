# 回测文档

本文档详细介绍Agentic Trader的回测功能，包括回测引擎、性能指标、可视化工具和使用示例。

## 目录

1. [概述](#概述)
2. [回测引擎](#回测引擎)
3. [性能指标](#性能指标)
4. [可视化工具](#可视化工具)
5. [使用示例](#使用示例)
6. [策略开发](#策略开发)
7. [最佳实践](#最佳实践)

---

## 概述

回测（Backtesting）是使用历史数据测试交易策略性能的过程。Agentic Trader提供了专业的回测引擎，帮助您：

- ✅ 验证策略有效性
- ✅ 评估风险收益特征
- ✅ 优化参数设置
- ✅ 避免过度拟合
- ✅ 了解策略行为

### 主要特性

| 特性 | 描述 |
|------|------|
| **真实成本模拟** | 包含手续费和滑点 |
| **专业指标** | 夏普比率、最大回撤等 |
| **可视化分析** | 权益曲线、回撤图表 |
| **灵活扩展** | 支持自定义策略 |
| **详细报告** | 完整的交易统计 |

---

## 回测引擎

### BacktestEngine类

位于：`agentic_trader/backtesting/engine.py`

#### 初始化

```python
from agentic_trader.backtesting.engine import BacktestEngine

engine = BacktestEngine(
    initial_capital=100000.0,    # 初始资金
    commission_rate=0.0003,      # 手续费率 (0.03%)
    slippage_rate=0.0005         # 滑点率 (0.05%)
)
```

#### 参数说明

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `initial_capital` | float | 100000.0 | 初始资金 (Rs.) |
| `commission_rate` | float | 0.0003 | 手续费率（双边） |
| `slippage_rate` | float | 0.0005 | 滑点率 |

### 执行交易

```python
engine.execute_trade(
    timestamp=datetime.now(),    # 交易时间
    symbol="ICICIBANK",          # 股票代码
    action="BUY",                # 买入/卖出
    quantity=10,                 # 数量
    price=1350.50                # 价格
)
```

### 交易成本计算

每笔交易的实际成本包括：

```python
# 买入
actual_price = price * (1 + slippage_rate)  # 加滑点
commission = quantity * actual_price * commission_rate

# 卖出
actual_price = price * (1 - slippage_rate)  # 减滑点
commission = quantity * actual_price * commission_rate
```

**示例**：

```
买入100股，价格1350.0
- 滑点 (0.05%): 1350.0 * 1.0005 = 1350.675
- 手续费 (0.03%): 100 * 1350.675 * 0.0003 = 40.52
- 总成本: 135067.5 + 40.52 = 135108.02
```

---

## 性能指标

### 计算指标

```python
result = engine.calculate_metrics()
```

### BacktestResult数据类

```python
@dataclass
class BacktestResult:
    # 收益指标
    initial_capital: float        # 初始资金
    final_capital: float          # 最终资金
    total_return: float           # 总收益
    total_return_pct: float       # 总收益率 (%)
    annualized_return: float      # 年化收益率 (%)

    # 风险指标
    max_drawdown: float           # 最大回撤 (Rs.)
    max_drawdown_pct: float       # 最大回撤率 (%)
    sharpe_ratio: float           # 夏普比率

    # 交易统计
    total_trades: int             # 总交易次数
    winning_trades: int           # 获利交易
    losing_trades: int            # 亏损交易
    win_rate: float               # 胜率 (%)
    profit_factor: float          # 盈亏比
    avg_profit: float             # 平均盈利
    avg_loss: float               # 平均亏损

    # 成本统计
    total_commission: float       # 总手续费
    total_slippage: float         # 总滑点

    # 时间序列
    equity_curve: pd.Series       # 权益曲线
```

### 关键指标解释

#### 1. 夏普比率 (Sharpe Ratio)

**公式**：
```
Sharpe Ratio = (年化收益率 - 无风险利率) / 年化波动率
```

**解读**：
- **< 1**: 风险调整后收益较差
- **1 - 2**: 良好
- **2 - 3**: 优秀
- **> 3**: 卓越

**示例**：
```python
# 假设年化收益15%，年化波动8%，无风险利率4%
sharpe = (0.15 - 0.04) / 0.08 = 1.375  # 良好
```

#### 2. 最大回撤 (Maximum Drawdown)

**定义**：权益曲线从峰值到谷底的最大下降幅度。

**公式**：
```
Max Drawdown = (谷底权益 - 峰值权益) / 峰值权益
```

**解读**：
- **< 10%**: 风险较低
- **10% - 20%**: 中等风险
- **> 20%**: 高风险

**示例**：
```python
# 权益从105000降至98000
drawdown = (98000 - 105000) / 105000 = -6.67%  # 风险较低
```

#### 3. 胜率 (Win Rate)

**公式**：
```
Win Rate = 获利交易数 / 总交易数 × 100%
```

**解读**：
- **> 60%**: 优秀
- **50% - 60%**: 良好
- **< 50%**: 需要配合高盈亏比

#### 4. 盈亏比 (Profit Factor)

**公式**：
```
Profit Factor = 总盈利 / 总亏损
```

**解读**：
- **> 2**: 优秀
- **1.5 - 2**: 良好
- **1 - 1.5**: 一般
- **< 1**: 策略亏损

---

## 可视化工具

### ChartGenerator类

位于：`agentic_trader/visualization/charts.py`

#### 初始化

```python
from agentic_trader.visualization.charts import ChartGenerator

chart_gen = ChartGenerator(output_dir="backtest_results")
```

#### 1. 权益曲线图

显示账户权益随时间的变化。

```python
chart_gen.plot_equity_curve(
    equity_series=result.equity_curve,
    title="RSI策略 - 权益曲线",
    filename="equity_curve.png"
)
```

**输出示例**：
- X轴：时间
- Y轴：账户权益
- 显示：初始/最终权益、总收益率、夏普比率

#### 2. 回撤分析图

显示账户回撤随时间的变化。

```python
chart_gen.plot_drawdown(
    equity_series=result.equity_curve,
    title="RSI策略 - 回撤分析",
    filename="drawdown.png"
)
```

**输出示例**：
- X轴：时间
- Y轴：回撤百分比
- 显示：最大回撤值和时间点

#### 3. 月度收益热力图

显示每月收益情况。

```python
daily_returns = result.equity_curve.pct_change().dropna()

chart_gen.plot_monthly_returns(
    daily_returns=daily_returns,
    title="RSI策略 - 月度收益",
    filename="monthly_returns.png"
)
```

**输出示例**：
- 行：年份
- 列：月份
- 颜色：绿色（盈利）/ 红色（亏损）

---

## 使用示例

### 完整回测流程

```python
import pandas as pd
from datetime import datetime
from agentic_trader.backtesting.engine import BacktestEngine
from agentic_trader.visualization.charts import ChartGenerator

# 1. 准备历史数据
data = pd.read_csv("ICICIBANK_5min.csv")
data['timestamp'] = pd.to_datetime(data['timestamp'])

# 2. 生成交易信号（示例：简单RSI策略）
def generate_signals(data):
    # 计算RSI
    delta = data['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    # 生成信号
    signals = []
    for i, row in data.iterrows():
        if rsi[i] < 30:  # 超卖
            signals.append(('BUY', row['timestamp'], row['close']))
        elif rsi[i] > 70:  # 超买
            signals.append(('SELL', row['timestamp'], row['close']))

    return signals

# 3. 初始化回测引擎
engine = BacktestEngine(
    initial_capital=100000.0,
    commission_rate=0.0003,
    slippage_rate=0.0005
)

# 4. 执行回测
signals = generate_signals(data)
position = 0  # 当前持仓

for action, timestamp, price in signals:
    if action == 'BUY' and position == 0:
        # 买入（使用50%资金）
        qty = int(engine.cash * 0.5 / price)
        if qty > 0:
            engine.execute_trade(timestamp, "ICICIBANK", "BUY", qty, price)
            position = qty

    elif action == 'SELL' and position > 0:
        # 卖出（平仓）
        engine.execute_trade(timestamp, "ICICIBANK", "SELL", position, price)
        position = 0

# 5. 计算性能指标
result = engine.calculate_metrics()

# 6. 打印结果
print(f"总收益率: {result.total_return_pct:.2f}%")
print(f"年化收益率: {result.annualized_return:.2f}%")
print(f"夏普比率: {result.sharpe_ratio:.2f}")
print(f"最大回撤: {result.max_drawdown_pct:.2f}%")
print(f"胜率: {result.win_rate:.2f}%")
print(f"盈亏比: {result.profit_factor:.2f}")

# 7. 生成图表
chart_gen = ChartGenerator(output_dir="results")
chart_gen.plot_equity_curve(result.equity_curve, "权益曲线", "equity.png")
chart_gen.plot_drawdown(result.equity_curve, "回撤分析", "drawdown.png")
```

---

## 策略开发

### 策略模板

```python
def my_strategy(data: pd.DataFrame) -> pd.DataFrame:
    """
    自定义策略模板

    Args:
        data: 包含OHLCV的DataFrame

    Returns:
        包含交易信号的DataFrame
    """
    signals = pd.DataFrame(index=data.index)
    signals['timestamp'] = data['timestamp']
    signals['symbol'] = data['symbol']
    signals['price'] = data['close']
    signals['signal'] = 'HOLD'

    # ===== 在这里实现您的策略逻辑 =====

    # 示例1: 均线交叉
    ma_short = data['close'].rolling(window=10).mean()
    ma_long = data['close'].rolling(window=30).mean()

    # 金叉 → BUY
    signals.loc[(ma_short > ma_long) & (ma_short.shift(1) <= ma_long.shift(1)), 'signal'] = 'BUY'

    # 死叉 → SELL
    signals.loc[(ma_short < ma_long) & (ma_short.shift(1) >= ma_long.shift(1)), 'signal'] = 'SELL'

    # ===== 策略逻辑结束 =====

    return signals
```

### 常见策略类型

#### 1. 趋势跟踪策略

```python
# 双均线策略
ma_fast = data['close'].ewm(span=12).mean()
ma_slow = data['close'].ewm(span=26).mean()

signals.loc[ma_fast > ma_slow, 'signal'] = 'BUY'
signals.loc[ma_fast < ma_slow, 'signal'] = 'SELL'
```

#### 2. 均值回归策略

```python
# 布林带策略
bb_middle = data['close'].rolling(20).mean()
bb_std = data['close'].rolling(20).std()
bb_upper = bb_middle + 2 * bb_std
bb_lower = bb_middle - 2 * bb_std

signals.loc[data['close'] < bb_lower, 'signal'] = 'BUY'   # 超卖
signals.loc[data['close'] > bb_upper, 'signal'] = 'SELL'  # 超买
```

#### 3. 动量策略

```python
# RSI + MACD组合
import talib

rsi = talib.RSI(data['close'], timeperiod=14)
macd, signal_line, _ = talib.MACD(data['close'])

# 同时满足：RSI超卖 + MACD看涨
buy_condition = (rsi < 30) & (macd > signal_line)
signals.loc[buy_condition, 'signal'] = 'BUY'

# 同时满足：RSI超买 + MACD看跌
sell_condition = (rsi > 70) & (macd < signal_line)
signals.loc[sell_condition, 'signal'] = 'SELL'
```

---

## 最佳实践

### 1. 数据质量

✅ **使用干净的数据**
- 处理缺失值
- 剔除异常值
- 对齐时间戳

❌ **避免**
- 使用未验证的数据
- 忽略数据质量问题

### 2. 避免过拟合

✅ **正确做法**
- 使用样本外测试
- 参数敏感性分析
- 保持策略简单

❌ **避免**
- 过度优化参数
- 使用太多指标
- 只在单一时间段测试

### 3. 真实成本

✅ **包含实际成本**
- 手续费
- 滑点
- 市场冲击

❌ **避免**
- 忽略交易成本
- 假设无限流动性

### 4. 风险管理

✅ **实施风险控制**
- 设置止损
- 限制仓位大小
- 分散投资

❌ **避免**
- 重仓单一股票
- 无止损机制

### 5. 样本外测试

✅ **数据分割**
```
训练集 (60%): 2020-2021
验证集 (20%): 2022
测试集 (20%): 2023
```

❌ **避免**
- 全部数据用于优化
- 没有预留测试集

---

## 示例脚本

查看完整的回测示例：

```bash
# 运行示例回测
python examples/run_backtest.py
```

脚本会生成：
- 权益曲线图
- 回撤分析图
- 月度收益热力图
- 文本格式报告

---

## 进阶主题

### 1. 多股票回测

```python
symbols = ["ICICIBANK", "RELIANCE", "SBIN"]

for symbol in symbols:
    data = load_data(symbol)
    signals = my_strategy(data)
    # 执行回测...
```

### 2. 参数优化

```python
from itertools import product

# 测试不同参数组合
rsi_periods = [10, 14, 20]
thresholds = [20, 30, 40]

best_sharpe = -999
best_params = None

for period, threshold in product(rsi_periods, thresholds):
    result = run_backtest(period, threshold)
    if result.sharpe_ratio > best_sharpe:
        best_sharpe = result.sharpe_ratio
        best_params = (period, threshold)

print(f"最佳参数: RSI={best_params[0]}, Threshold={best_params[1]}")
```

### 3. 前瞻偏差检测

确保策略不使用"未来"数据：

```python
# ✅ 正确：只使用历史数据
ma = data['close'].shift(1).rolling(20).mean()

# ❌ 错误：使用了当前数据
ma = data['close'].rolling(20).mean()  # 包含当前K线
```

---

## 常见问题

**Q: 回测表现好，实盘表现差？**

A: 可能原因：
1. 过拟合历史数据
2. 忽略交易成本
3. 滑点估计不足
4. 市场环境变化

**Q: 如何评估策略稳定性？**

A: 使用以下方法：
1. 蒙特卡洛模拟
2. 滚动窗口测试
3. 参数敏感性分析
4. 不同市场环境测试

**Q: 夏普比率多少算好？**

A: 参考标准：
- < 1: 需要改进
- 1-2: 良好
- 2-3: 优秀
- \> 3: 卓越

---

## 资源

- 示例代码: `examples/run_backtest.py`
- 引擎源码: `agentic_trader/backtesting/engine.py`
- 可视化源码: `agentic_trader/visualization/charts.py`
- 测试用例: `agentic_trader/tests/test_integration.py`

---

## 下一步

1. 运行示例回测脚本
2. 开发自己的策略
3. 优化参数设置
4. 进行样本外测试
5. 实盘前进行模拟交易

祝您回测愉快！📈
