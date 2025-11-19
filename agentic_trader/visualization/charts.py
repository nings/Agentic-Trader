"""图表生成工具"""

import logging
from typing import Optional
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)


class ChartGenerator:
    """图表生成器"""

    def __init__(self, output_dir: str = "reports/charts"):
        """
        初始化图表生成器

        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 设置样式
        plt.style.use('seaborn-v0_8-darkgrid')

    def plot_equity_curve(
        self,
        equity_series: pd.Series,
        title: str = "Equity Curve",
        filename: Optional[str] = None
    ) -> str:
        """
        绘制权益曲线

        Args:
            equity_series: 权益时间序列
            title: 图表标题
            filename: 保存文件名

        Returns:
            保存的文件路径
        """
        fig, ax = plt.subplots(figsize=(12, 6))

        ax.plot(equity_series.index, equity_series.values, linewidth=2, color='#2E86AB')
        ax.fill_between(equity_series.index, equity_series.values, alpha=0.3, color='#2E86AB')

        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Equity (Rs.)', fontsize=12)
        ax.grid(True, alpha=0.3)

        # 格式化日期
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.xticks(rotation=45)

        # 添加统计信息
        initial = equity_series.iloc[0]
        final = equity_series.iloc[-1]
        total_return = ((final - initial) / initial) * 100

        textstr = f'Initial: Rs.{initial:,.0f}\nFinal: Rs.{final:,.0f}\nReturn: {total_return:+.2f}%'
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=props)

        plt.tight_layout()

        # 保存
        if filename is None:
            filename = "equity_curve.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"Equity curve saved to {filepath}")
        return str(filepath)

    def plot_drawdown(
        self,
        equity_series: pd.Series,
        title: str = "Drawdown",
        filename: Optional[str] = None
    ) -> str:
        """
        绘制回撤图

        Args:
            equity_series: 权益时间序列
            title: 图表标题
            filename: 保存文件名

        Returns:
            保存的文件路径
        """
        fig, ax = plt.subplots(figsize=(12, 6))

        # 计算回撤
        running_max = equity_series.cummax()
        drawdown = (equity_series - running_max) / running_max * 100

        ax.fill_between(drawdown.index, 0, drawdown.values, alpha=0.5, color='#A23B72')
        ax.plot(drawdown.index, drawdown.values, linewidth=1, color='#A23B72')

        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Drawdown (%)', fontsize=12)
        ax.grid(True, alpha=0.3)

        # 格式化日期
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.xticks(rotation=45)

        # 添加最大回撤信息
        max_dd = drawdown.min()
        max_dd_date = drawdown.idxmin()

        textstr = f'Max Drawdown: {max_dd:.2f}%\nDate: {max_dd_date.strftime("%Y-%m-%d")}'
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
        ax.text(0.02, 0.02, textstr, transform=ax.transAxes, fontsize=10,
                verticalalignment='bottom', bbox=props)

        plt.tight_layout()

        # 保存
        if filename is None:
            filename = "drawdown.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"Drawdown chart saved to {filepath}")
        return str(filepath)

    def plot_monthly_returns(
        self,
        daily_returns: pd.Series,
        title: str = "Monthly Returns Heatmap",
        filename: Optional[str] = None
    ) -> str:
        """
        绘制月度收益热力图

        Args:
            daily_returns: 日收益率序列
            title: 图表标题
            filename: 保存文件名

        Returns:
            保存的文件路径
        """
        # 计算月度收益
        monthly_returns = daily_returns.resample('M').apply(lambda x: (1 + x).prod() - 1) * 100

        # 创建年月矩阵
        returns_matrix = monthly_returns.groupby([monthly_returns.index.year, monthly_returns.index.month]).first().unstack()

        fig, ax = plt.subplots(figsize=(14, 8))

        # 绘制热力图
        im = ax.imshow(returns_matrix.T, cmap='RdYlGn', aspect='auto', vmin=-10, vmax=10)

        # 设置坐标轴
        ax.set_xticks(range(len(returns_matrix.index)))
        ax.set_yticks(range(12))
        ax.set_xticklabels(returns_matrix.index)
        ax.set_yticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])

        # 添加数值
        for i in range(len(returns_matrix.index)):
            for j in range(12):
                if not pd.isna(returns_matrix.T.iloc[j, i]):
                    text = ax.text(i, j, f'{returns_matrix.T.iloc[j, i]:.1f}%',
                                 ha="center", va="center", color="black", fontsize=8)

        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.set_xlabel('Year', fontsize=12)
        ax.set_ylabel('Month', fontsize=12)

        # 添加颜色条
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Return (%)', rotation=270, labelpad=15)

        plt.tight_layout()

        # 保存
        if filename is None:
            filename = "monthly_returns.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"Monthly returns heatmap saved to {filepath}")
        return str(filepath)
