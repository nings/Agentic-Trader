"""
回测示例脚本

演示如何使用BacktestEngine进行策略回测和性能分析
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

from agentic_trader.backtesting.engine import BacktestEngine
from agentic_trader.visualization.charts import ChartGenerator


def generate_sample_data(symbol: str, days: int = 30) -> pd.DataFrame:
    """
    生成示例市场数据

    Args:
        symbol: 股票代码
        days: 天数

    Returns:
        包含OHLCV数据的DataFrame
    """
    # 生成时间序列（5分钟K线）
    periods = days * 78  # 每天78个5分钟K线（9:15-15:30）
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    timestamps = pd.date_range(start=start_time, end=end_time, periods=periods)

    # 生成价格数据（随机游走）
    base_price = 1350.0 if symbol == "ICICIBANK" else 2450.0
    returns = np.random.randn(periods) * 0.002  # 0.2%波动率
    close_prices = base_price * (1 + returns).cumprod()

    # 生成OHLC
    high_prices = close_prices + np.random.rand(periods) * 5
    low_prices = close_prices - np.random.rand(periods) * 5
    open_prices = close_prices + np.random.randn(periods) * 2
    volume = np.random.randint(10000, 100000, periods)

    return pd.DataFrame({
        'timestamp': timestamps,
        'symbol': symbol,
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volume
    })


def simple_rsi_strategy(data: pd.DataFrame, rsi_period: int = 14) -> pd.DataFrame:
    """
    简单RSI策略

    买入信号：RSI < 30（超卖）
    卖出信号：RSI > 70（超买）

    Args:
        data: 市场数据
        rsi_period: RSI周期

    Returns:
        包含交易信号的DataFrame
    """
    # 计算RSI
    close = data['close']
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    # 生成信号
    signals = pd.DataFrame(index=data.index)
    signals['timestamp'] = data['timestamp']
    signals['symbol'] = data['symbol']
    signals['price'] = data['close']
    signals['signal'] = 'HOLD'

    # RSI < 30 → BUY
    signals.loc[rsi < 30, 'signal'] = 'BUY'

    # RSI > 70 → SELL
    signals.loc[rsi > 70, 'signal'] = 'SELL'

    return signals


def macd_strategy(data: pd.DataFrame) -> pd.DataFrame:
    """
    MACD交叉策略

    买入信号：MACD上穿信号线
    卖出信号：MACD下穿信号线

    Args:
        data: 市场数据

    Returns:
        包含交易信号的DataFrame
    """
    close = data['close']

    # 计算MACD
    ema_12 = close.ewm(span=12).mean()
    ema_26 = close.ewm(span=26).mean()
    macd = ema_12 - ema_26
    signal_line = macd.ewm(span=9).mean()

    # 检测交叉
    signals = pd.DataFrame(index=data.index)
    signals['timestamp'] = data['timestamp']
    signals['symbol'] = data['symbol']
    signals['price'] = data['close']
    signals['signal'] = 'HOLD'

    # MACD上穿信号线 → BUY
    signals.loc[(macd > signal_line) & (macd.shift(1) <= signal_line.shift(1)), 'signal'] = 'BUY'

    # MACD下穿信号线 → SELL
    signals.loc[(macd < signal_line) & (macd.shift(1) >= signal_line.shift(1)), 'signal'] = 'SELL'

    return signals


def run_backtest_example():
    """运行回测示例"""

    print("=" * 60)
    print("Agentic Trader - 回测示例")
    print("=" * 60)

    # 1. 生成示例数据
    print("\n[1/6] 生成示例市场数据...")
    symbol = "ICICIBANK"
    data = generate_sample_data(symbol, days=30)
    print(f"  ✓ 生成 {len(data)} 条{symbol}的5分钟K线数据")

    # 2. 生成交易信号（RSI策略）
    print("\n[2/6] 生成交易信号（RSI策略）...")
    signals = simple_rsi_strategy(data)
    buy_signals = len(signals[signals['signal'] == 'BUY'])
    sell_signals = len(signals[signals['signal'] == 'SELL'])
    print(f"  ✓ 生成 {buy_signals} 个买入信号，{sell_signals} 个卖出信号")

    # 3. 初始化回测引擎
    print("\n[3/6] 初始化回测引擎...")
    engine = BacktestEngine(
        initial_capital=100000.0,
        commission_rate=0.0003,  # 0.03%手续费
        slippage_rate=0.0005     # 0.05%滑点
    )
    print(f"  ✓ 初始资金: Rs.{engine.initial_capital:,.2f}")
    print(f"  ✓ 手续费率: {engine.commission_rate*100:.3f}%")
    print(f"  ✓ 滑点率: {engine.slippage_rate*100:.3f}%")

    # 4. 执行回测
    print("\n[4/6] 执行回测...")
    position_qty = 0  # 当前持仓
    trade_count = 0

    for _, signal_row in signals.iterrows():
        timestamp = signal_row['timestamp']
        symbol = signal_row['symbol']
        price = signal_row['price']
        signal = signal_row['signal']

        if signal == 'BUY' and position_qty == 0:
            # 买入（使用可用资金的50%）
            max_qty = int(engine.cash * 0.5 / price)
            if max_qty > 0:
                engine.execute_trade(timestamp, symbol, 'BUY', max_qty, price)
                position_qty = max_qty
                trade_count += 1

        elif signal == 'SELL' and position_qty > 0:
            # 卖出（平仓）
            engine.execute_trade(timestamp, symbol, 'SELL', position_qty, price)
            position_qty = 0
            trade_count += 1

    # 如果有持仓，在最后平仓
    if position_qty > 0:
        final_price = data['close'].iloc[-1]
        engine.execute_trade(data['timestamp'].iloc[-1], symbol, 'SELL', position_qty, final_price)
        trade_count += 1

    print(f"  ✓ 执行了 {trade_count} 笔交易")

    # 5. 计算性能指标
    print("\n[5/6] 计算性能指标...")
    result = engine.calculate_metrics()

    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)
    print(f"\n【收益指标】")
    print(f"  初始资金:        Rs.{engine.initial_capital:>12,.2f}")
    print(f"  最终资金:        Rs.{result.final_capital:>12,.2f}")
    print(f"  总收益:          Rs.{result.total_return:>12,.2f}")
    print(f"  总收益率:        {result.total_return_pct:>12.2f}%")
    print(f"  年化收益率:      {result.annualized_return:>12.2f}%")

    print(f"\n【风险指标】")
    print(f"  最大回撤:        Rs.{result.max_drawdown:>12,.2f}")
    print(f"  最大回撤率:      {result.max_drawdown_pct:>12.2f}%")
    print(f"  夏普比率:        {result.sharpe_ratio:>12.2f}")

    print(f"\n【交易统计】")
    print(f"  总交易次数:      {result.total_trades:>12}")
    print(f"  获利交易:        {result.winning_trades:>12}")
    print(f"  亏损交易:        {result.losing_trades:>12}")
    print(f"  胜率:            {result.win_rate:>12.2f}%")
    print(f"  盈亏比:          {result.profit_factor:>12.2f}")
    print(f"  平均收益:        Rs.{result.avg_profit:>12,.2f}")
    print(f"  平均亏损:        Rs.{result.avg_loss:>12,.2f}")

    print(f"\n【手续费统计】")
    print(f"  总手续费:        Rs.{result.total_commission:>12,.2f}")
    print(f"  总滑点:          Rs.{result.total_slippage:>12,.2f}")
    print(f"  总成本:          Rs.{result.total_commission + result.total_slippage:>12,.2f}")

    # 6. 生成可视化图表
    print("\n[6/6] 生成可视化图表...")
    output_dir = Path("backtest_results")
    output_dir.mkdir(exist_ok=True)

    chart_gen = ChartGenerator(output_dir=str(output_dir))

    # 权益曲线
    chart_gen.plot_equity_curve(
        equity_series=result.equity_curve,
        title=f"{symbol} - RSI策略回测 - 权益曲线",
        filename="equity_curve.png"
    )
    print(f"  ✓ 权益曲线图已保存: {output_dir}/equity_curve.png")

    # 回撤图
    chart_gen.plot_drawdown(
        equity_series=result.equity_curve,
        title=f"{symbol} - RSI策略回测 - 回撤分析",
        filename="drawdown.png"
    )
    print(f"  ✓ 回撤分析图已保存: {output_dir}/drawdown.png")

    # 月度收益热力图
    if len(result.equity_curve) > 0:
        daily_returns = result.equity_curve.pct_change().dropna()
        chart_gen.plot_monthly_returns(
            daily_returns=daily_returns,
            title=f"{symbol} - RSI策略回测 - 月度收益",
            filename="monthly_returns.png"
        )
        print(f"  ✓ 月度收益图已保存: {output_dir}/monthly_returns.png")

    # 保存回测报告
    report_path = output_dir / "backtest_report.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("Agentic Trader - 回测报告\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"策略: RSI超买超卖策略\n")
        f.write(f"股票: {symbol}\n")
        f.write(f"回测期间: {data['timestamp'].iloc[0]} ~ {data['timestamp'].iloc[-1]}\n")
        f.write(f"数据条数: {len(data)}\n\n")
        f.write(f"总收益率: {result.total_return_pct:.2f}%\n")
        f.write(f"年化收益率: {result.annualized_return:.2f}%\n")
        f.write(f"夏普比率: {result.sharpe_ratio:.2f}\n")
        f.write(f"最大回撤: {result.max_drawdown_pct:.2f}%\n")
        f.write(f"胜率: {result.win_rate:.2f}%\n")
        f.write(f"盈亏比: {result.profit_factor:.2f}\n")

    print(f"  ✓ 回测报告已保存: {report_path}")

    print("\n" + "=" * 60)
    print("回测完成！")
    print("=" * 60)


if __name__ == "__main__":
    run_backtest_example()
