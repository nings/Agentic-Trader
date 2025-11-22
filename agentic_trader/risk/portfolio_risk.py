"""投资组合风险分析器"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PortfolioRiskMetrics:
    """投资组合风险指标"""
    total_value: float
    total_risk: float
    var_95: float
    var_99: float
    cvar_95: float
    portfolio_volatility: float
    beta: float
    sharpe_ratio: float
    max_drawdown: float
    concentration_risk: Dict[str, float]
    correlation_matrix: Optional[pd.DataFrame] = None


class PortfolioRiskAnalyzer:
    """
    投资组合风险分析器

    分析整体投资组合的风险暴露
    """

    def __init__(self, risk_free_rate: float = 0.04):
        """
        初始化分析器

        Args:
            risk_free_rate: 无风险利率（年化）
        """
        self.risk_free_rate = risk_free_rate

    def analyze(
        self,
        positions: Dict[str, Dict],  # {symbol: {quantity, price, value}}
        returns_history: Dict[str, pd.Series],  # {symbol: returns}
        market_returns: Optional[pd.Series] = None
    ) -> PortfolioRiskMetrics:
        """
        分析投资组合风险

        Args:
            positions: 持仓字典
            returns_history: 历史收益率
            market_returns: 市场收益率（计算Beta用）

        Returns:
            风险指标
        """
        # 计算投资组合总价值
        total_value = sum(pos['value'] for pos in positions.values())

        if total_value == 0:
            logger.warning("Portfolio value is zero")
            return self._get_empty_metrics()

        # 计算权重
        weights = {
            symbol: pos['value'] / total_value
            for symbol, pos in positions.items()
        }

        # 计算投资组合收益率
        portfolio_returns = self._calculate_portfolio_returns(
            weights, returns_history
        )

        # 计算VaR
        from .var_calculator import VaRCalculator
        var_calc = VaRCalculator(confidence_level=0.95)

        var_95_result = var_calc.historical_var(portfolio_returns, total_value)
        var_95 = var_95_result['var_amount']

        var_calc_99 = VaRCalculator(confidence_level=0.99)
        var_99_result = var_calc_99.historical_var(portfolio_returns, total_value)
        var_99 = var_99_result['var_amount']

        cvar_result = var_calc.conditional_var(portfolio_returns, total_value)
        cvar_95 = cvar_result['cvar_amount']

        # 计算波动率
        portfolio_volatility = portfolio_returns.std() * np.sqrt(252)  # 年化

        # 计算Beta（如果有市场收益率）
        beta = self._calculate_beta(portfolio_returns, market_returns)

        # 计算夏普比率
        excess_returns = portfolio_returns.mean() - self.risk_free_rate / 252
        sharpe_ratio = (
            excess_returns / portfolio_returns.std() * np.sqrt(252)
            if portfolio_returns.std() > 0 else 0.0
        )

        # 计算最大回撤
        cumulative_returns = (1 + portfolio_returns).cumprod()
        running_max = cumulative_returns.cummax()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min()

        # 集中度风险
        concentration_risk = self._analyze_concentration(weights)

        # 相关性矩阵
        correlation_matrix = self._calculate_correlation_matrix(returns_history)

        logger.info(
            f"Portfolio risk analysis: VaR(95%)={var_95:,.2f}, "
            f"Vol={portfolio_volatility*100:.2f}%, Sharpe={sharpe_ratio:.2f}"
        )

        return PortfolioRiskMetrics(
            total_value=total_value,
            total_risk=var_95,
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            portfolio_volatility=portfolio_volatility,
            beta=beta,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            concentration_risk=concentration_risk,
            correlation_matrix=correlation_matrix
        )

    def _calculate_portfolio_returns(
        self,
        weights: Dict[str, float],
        returns_history: Dict[str, pd.Series]
    ) -> pd.Series:
        """
        计算投资组合收益率

        Args:
            weights: 权重字典
            returns_history: 历史收益率

        Returns:
            投资组合收益率序列
        """
        # 对齐所有收益率序列
        returns_df = pd.DataFrame(returns_history)

        # 计算加权收益率
        portfolio_returns = sum(
            returns_df[symbol] * weight
            for symbol, weight in weights.items()
            if symbol in returns_df.columns
        )

        return portfolio_returns.dropna()

    def _calculate_beta(
        self,
        portfolio_returns: pd.Series,
        market_returns: Optional[pd.Series]
    ) -> float:
        """
        计算投资组合Beta

        Args:
            portfolio_returns: 投资组合收益率
            market_returns: 市场收益率

        Returns:
            Beta值
        """
        if market_returns is None or len(market_returns) == 0:
            return 1.0

        # 对齐数据
        aligned = pd.DataFrame({
            'portfolio': portfolio_returns,
            'market': market_returns
        }).dropna()

        if len(aligned) < 10:
            return 1.0

        # Beta = Cov(Rp, Rm) / Var(Rm)
        covariance = aligned['portfolio'].cov(aligned['market'])
        market_variance = aligned['market'].var()

        beta = covariance / market_variance if market_variance > 0 else 1.0

        return beta

    def _analyze_concentration(
        self,
        weights: Dict[str, float]
    ) -> Dict[str, float]:
        """
        分析集中度风险

        Args:
            weights: 权重字典

        Returns:
            集中度指标
        """
        weight_values = list(weights.values())

        # Herfindahl指数（越高越集中）
        herfindahl_index = sum(w ** 2 for w in weight_values)

        # 有效资产数量
        effective_n = 1 / herfindahl_index if herfindahl_index > 0 else 0

        # 最大权重
        max_weight = max(weight_values) if weight_values else 0

        # Top 3权重占比
        top_3_weight = sum(sorted(weight_values, reverse=True)[:3])

        return {
            'herfindahl_index': herfindahl_index,
            'effective_n_assets': effective_n,
            'max_single_weight': max_weight,
            'top_3_weight': top_3_weight,
            'diversification_ratio': 1 - herfindahl_index
        }

    def _calculate_correlation_matrix(
        self,
        returns_history: Dict[str, pd.Series]
    ) -> pd.DataFrame:
        """
        计算相关性矩阵

        Args:
            returns_history: 历史收益率

        Returns:
            相关性矩阵
        """
        returns_df = pd.DataFrame(returns_history)
        correlation_matrix = returns_df.corr()

        return correlation_matrix

    def _get_empty_metrics(self) -> PortfolioRiskMetrics:
        """返回空的风险指标"""
        return PortfolioRiskMetrics(
            total_value=0.0,
            total_risk=0.0,
            var_95=0.0,
            var_99=0.0,
            cvar_95=0.0,
            portfolio_volatility=0.0,
            beta=1.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            concentration_risk={}
        )

    def check_diversification(
        self,
        weights: Dict[str, float],
        correlation_matrix: pd.DataFrame,
        max_correlation: float = 0.7,
        max_single_weight: float = 0.3
    ) -> Dict[str, any]:
        """
        检查分散化程度

        Args:
            weights: 权重字典
            correlation_matrix: 相关性矩阵
            max_correlation: 最大相关系数阈值
            max_single_weight: 单一资产最大权重

        Returns:
            分散化检查结果
        """
        warnings = []

        # 检查单一资产权重
        for symbol, weight in weights.items():
            if weight > max_single_weight:
                warnings.append({
                    'type': 'concentration',
                    'message': f"{symbol} weight ({weight*100:.1f}%) exceeds threshold ({max_single_weight*100:.1f}%)"
                })

        # 检查高相关性
        symbols = list(weights.keys())
        for i, symbol1 in enumerate(symbols):
            for symbol2 in symbols[i+1:]:
                if symbol1 in correlation_matrix.index and symbol2 in correlation_matrix.columns:
                    corr = correlation_matrix.loc[symbol1, symbol2]
                    if abs(corr) > max_correlation:
                        warnings.append({
                            'type': 'high_correlation',
                            'message': f"High correlation between {symbol1} and {symbol2}: {corr:.2f}"
                        })

        return {
            'is_diversified': len(warnings) == 0,
            'warnings': warnings,
            'num_assets': len(weights),
            'effective_n_assets': self._analyze_concentration(weights)['effective_n_assets']
        }
