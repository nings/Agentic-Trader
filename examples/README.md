# 示例脚本

本目录包含Agentic Trader的使用示例。

## 回测示例

### run_backtest.py

演示如何使用BacktestEngine进行策略回测和性能分析。

**功能特点**：
- 生成模拟市场数据
- 实现简单的RSI和MACD交易策略
- 执行完整的回测流程
- 计算专业的性能指标（夏普比率、最大回撤、胜率、盈亏比等）
- 生成可视化图表（权益曲线、回撤分析、月度收益热力图）

**运行方式**：

```bash
# 从项目根目录运行
python examples/run_backtest.py
```

**输出**：

脚本会在`backtest_results/`目录下生成：
- `equity_curve.png` - 权益曲线图
- `drawdown.png` - 回撤分析图
- `monthly_returns.png` - 月度收益热力图
- `backtest_report.txt` - 文本格式的回测报告

**示例输出**：

```
============================================================
Agentic Trader - 回测示例
============================================================

[1/6] 生成示例市场数据...
  ✓ 生成 2340 条ICICIBANK的5分钟K线数据

[2/6] 生成交易信号（RSI策略）...
  ✓ 生成 25 个买入信号，23 个卖出信号

[3/6] 初始化回测引擎...
  ✓ 初始资金: Rs.100,000.00
  ✓ 手续费率: 0.030%
  ✓ 滑点率: 0.050%

[4/6] 执行回测...
  ✓ 执行了 48 笔交易

[5/6] 计算性能指标...

============================================================
回测结果
============================================================

【收益指标】
  初始资金:        Rs.  100,000.00
  最终资金:        Rs.  105,234.56
  总收益:          Rs.    5,234.56
  总收益率:                 5.23%
  年化收益率:              63.45%

【风险指标】
  最大回撤:        Rs.    2,345.67
  最大回撤率:               2.35%
  夏普比率:                 2.15

【交易统计】
  总交易次数:                48
  获利交易:                  28
  亏损交易:                  20
  胜率:                   58.33%
  盈亏比:                   1.45
  平均收益:        Rs.      325.50
  平均亏损:        Rs.     -224.25

【手续费统计】
  总手续费:        Rs.      156.78
  总滑点:          Rs.      261.30
  总成本:          Rs.      418.08

[6/6] 生成可视化图表...
  ✓ 权益曲线图已保存: backtest_results/equity_curve.png
  ✓ 回撤分析图已保存: backtest_results/drawdown.png
  ✓ 月度收益图已保存: backtest_results/monthly_returns.png
  ✓ 回测报告已保存: backtest_results/backtest_report.txt

============================================================
回测完成！
============================================================
```

## 自定义策略

您可以在`run_backtest.py`的基础上实现自己的交易策略：

```python
def my_custom_strategy(data: pd.DataFrame) -> pd.DataFrame:
    """自定义策略"""
    signals = pd.DataFrame(index=data.index)
    signals['timestamp'] = data['timestamp']
    signals['symbol'] = data['symbol']
    signals['price'] = data['close']
    signals['signal'] = 'HOLD'

    # 在这里实现您的策略逻辑
    # 例如：双均线交叉
    ma_short = data['close'].rolling(window=10).mean()
    ma_long = data['close'].rolling(window=30).mean()

    # 短期均线上穿长期均线 → BUY
    signals.loc[(ma_short > ma_long) & (ma_short.shift(1) <= ma_long.shift(1)), 'signal'] = 'BUY'

    # 短期均线下穿长期均线 → SELL
    signals.loc[(ma_short < ma_long) & (ma_short.shift(1) >= ma_long.shift(1)), 'signal'] = 'SELL'

    return signals
```

## 其他示例

更多示例正在开发中，包括：
- 实时交易示例
- 多策略组合示例
- 风险管理示例
- 指标计算示例
