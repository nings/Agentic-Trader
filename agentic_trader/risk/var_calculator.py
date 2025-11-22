"""VaR（风险价值）计算器"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from scipy import stats

logger = logging.getLogger(__name__)


class VaRCalculator:
    """
    风险价值（Value at Risk, VaR）计算器

    计算投资组合在给定置信水平下的最大可能损失
    """

    def __init__(self, confidence_level: float = 0.95):
        """
        初始化VaR计算器

        Args:
            confidence_level: 置信水平（默认95%）
        """
        self.confidence_level = confidence_level
        self.alpha = 1 - confidence_level

    def historical_var(
        self,
        returns: pd.Series,
        portfolio_value: float
    ) -> Dict[str, float]:
        """
        历史模拟法计算VaR

        Args:
            returns: 历史收益率序列
            portfolio_value: 投资组合价值

        Returns:
            VaR结果字典
        """
        if len(returns) < 10:
            logger.warning("Insufficient data for historical VaR calculation")
            return {
                'var_amount': 0.0,
                'var_pct': 0.0,
                'method': 'historical',
                'confidence_level': self.confidence_level
            }

        # 计算分位数
        var_pct = np.percentile(returns, self.alpha * 100)
        var_amount = abs(var_pct * portfolio_value)

        logger.debug(
            f"Historical VaR at {self.confidence_level*100}% confidence: "
            f"Rs.{var_amount:,.2f} ({var_pct*100:.2f}%)"
        )

        return {
            'var_amount': var_amount,
            'var_pct': abs(var_pct),
            'method': 'historical',
            'confidence_level': self.confidence_level,
            'percentile': self.alpha * 100
        }

    def parametric_var(
        self,
        returns: pd.Series,
        portfolio_value: float
    ) -> Dict[str, float]:
        """
        参数法（方差-协方差法）计算VaR

        假设收益率服从正态分布

        Args:
            returns: 历史收益率序列
            portfolio_value: 投资组合价值

        Returns:
            VaR结果字典
        """
        if len(returns) < 10:
            logger.warning("Insufficient data for parametric VaR calculation")
            return {
                'var_amount': 0.0,
                'var_pct': 0.0,
                'method': 'parametric',
                'confidence_level': self.confidence_level
            }

        # 计算均值和标准差
        mu = returns.mean()
        sigma = returns.std()

        # 计算Z分数
        z_score = stats.norm.ppf(self.alpha)

        # VaR = -μ + σ * Z
        var_pct = -(mu + sigma * z_score)
        var_amount = var_pct * portfolio_value

        logger.debug(
            f"Parametric VaR at {self.confidence_level*100}% confidence: "
            f"Rs.{var_amount:,.2f} ({var_pct*100:.2f}%)"
        )

        return {
            'var_amount': var_amount,
            'var_pct': var_pct,
            'method': 'parametric',
            'confidence_level': self.confidence_level,
            'mean_return': mu,
            'volatility': sigma,
            'z_score': z_score
        }

    def monte_carlo_var(
        self,
        returns: pd.Series,
        portfolio_value: float,
        num_simulations: int = 10000,
        time_horizon: int = 1
    ) -> Dict[str, float]:
        """
        蒙特卡洛模拟法计算VaR

        Args:
            returns: 历史收益率序列
            portfolio_value: 投资组合价值
            num_simulations: 模拟次数
            time_horizon: 时间窗口（天）

        Returns:
            VaR结果字典
        """
        if len(returns) < 10:
            logger.warning("Insufficient data for Monte Carlo VaR calculation")
            return {
                'var_amount': 0.0,
                'var_pct': 0.0,
                'method': 'monte_carlo',
                'confidence_level': self.confidence_level
            }

        # 计算收益率的均值和标准差
        mu = returns.mean()
        sigma = returns.std()

        # 蒙特卡洛模拟
        simulated_returns = np.random.normal(
            mu * time_horizon,
            sigma * np.sqrt(time_horizon),
            num_simulations
        )

        # 计算VaR
        var_pct = abs(np.percentile(simulated_returns, self.alpha * 100))
        var_amount = var_pct * portfolio_value

        logger.debug(
            f"Monte Carlo VaR ({num_simulations} simulations) at "
            f"{self.confidence_level*100}% confidence: "
            f"Rs.{var_amount:,.2f} ({var_pct*100:.2f}%)"
        )

        return {
            'var_amount': var_amount,
            'var_pct': var_pct,
            'method': 'monte_carlo',
            'confidence_level': self.confidence_level,
            'num_simulations': num_simulations,
            'time_horizon': time_horizon
        }

    def conditional_var(
        self,
        returns: pd.Series,
        portfolio_value: float
    ) -> Dict[str, float]:
        """
        条件风险价值（CVaR，又称Expected Shortfall）

        计算超过VaR的平均损失

        Args:
            returns: 历史收益率序列
            portfolio_value: 投资组合价值

        Returns:
            CVaR结果字典
        """
        if len(returns) < 10:
            logger.warning("Insufficient data for CVaR calculation")
            return {
                'cvar_amount': 0.0,
                'cvar_pct': 0.0,
                'method': 'conditional',
                'confidence_level': self.confidence_level
            }

        # 首先计算VaR
        var_result = self.historical_var(returns, portfolio_value)
        var_pct = var_result['var_pct']

        # CVaR = 超过VaR的损失的平均值
        worst_returns = returns[returns <= -var_pct]

        if len(worst_returns) > 0:
            cvar_pct = abs(worst_returns.mean())
        else:
            cvar_pct = var_pct

        cvar_amount = cvar_pct * portfolio_value

        logger.debug(
            f"CVaR at {self.confidence_level*100}% confidence: "
            f"Rs.{cvar_amount:,.2f} ({cvar_pct*100:.2f}%)"
        )

        return {
            'cvar_amount': cvar_amount,
            'cvar_pct': cvar_pct,
            'var_amount': var_result['var_amount'],
            'var_pct': var_pct,
            'method': 'conditional',
            'confidence_level': self.confidence_level
        }

    def calculate_all_methods(
        self,
        returns: pd.Series,
        portfolio_value: float
    ) -> Dict[str, Dict[str, float]]:
        """
        使用所有方法计算VaR

        Args:
            returns: 历史收益率序列
            portfolio_value: 投资组合价值

        Returns:
            包含所有方法结果的字典
        """
        results = {
            'historical': self.historical_var(returns, portfolio_value),
            'parametric': self.parametric_var(returns, portfolio_value),
            'monte_carlo': self.monte_carlo_var(returns, portfolio_value),
            'conditional': self.conditional_var(returns, portfolio_value)
        }

        # 计算平均VaR
        var_amounts = [
            results['historical']['var_amount'],
            results['parametric']['var_amount'],
            results['monte_carlo']['var_amount']
        ]
        avg_var = np.mean(var_amounts)

        results['average'] = {
            'var_amount': avg_var,
            'var_pct': avg_var / portfolio_value,
            'method': 'average'
        }

        return results

    def backtest_var(
        self,
        historical_returns: pd.Series,
        var_estimates: pd.Series
    ) -> Dict[str, float]:
        """
        VaR模型回测

        Args:
            historical_returns: 历史收益率
            var_estimates: VaR估计值

        Returns:
            回测结果
        """
        # 计算违约次数（实际损失超过VaR的次数）
        violations = (historical_returns < -var_estimates).sum()
        total_days = len(historical_returns)

        violation_rate = violations / total_days
        expected_rate = self.alpha

        # Kupiec检验（比例似然比检验）
        if violations > 0:
            lr_stat = -2 * np.log(
                (expected_rate ** violations) *
                ((1 - expected_rate) ** (total_days - violations))
            ) + 2 * np.log(
                (violation_rate ** violations) *
                ((1 - violation_rate) ** (total_days - violations))
            )
        else:
            lr_stat = 0.0

        # p值（卡方分布，自由度=1）
        p_value = 1 - stats.chi2.cdf(lr_stat, df=1)

        return {
            'violations': violations,
            'total_days': total_days,
            'violation_rate': violation_rate,
            'expected_rate': expected_rate,
            'lr_statistic': lr_stat,
            'p_value': p_value,
            'model_adequate': p_value > 0.05  # 5%显著性水平
        }


class PortfolioVolatilityEstimator:
    """投资组合波动率估计器"""

    @staticmethod
    def ewma_volatility(
        returns: pd.Series,
        lambda_decay: float = 0.94
    ) -> pd.Series:
        """
        指数加权移动平均（EWMA）波动率

        Args:
            returns: 收益率序列
            lambda_decay: 衰减因子（默认0.94，RiskMetrics推荐）

        Returns:
            波动率序列
        """
        # EWMA方差
        var_ewma = returns.var()  # 初始值
        variance_series = []

        for ret in returns:
            var_ewma = lambda_decay * var_ewma + (1 - lambda_decay) * ret ** 2
            variance_series.append(var_ewma)

        # 转换为波动率
        volatility = np.sqrt(pd.Series(variance_series))

        return volatility

    @staticmethod
    def garch_volatility(
        returns: pd.Series,
        p: int = 1,
        q: int = 1
    ) -> pd.Series:
        """
        GARCH(p,q)波动率模型

        需要arch包：pip install arch

        Args:
            returns: 收益率序列
            p: ARCH项数
            q: GARCH项数

        Returns:
            条件波动率序列
        """
        try:
            from arch import arch_model

            # 拟合GARCH模型
            model = arch_model(returns * 100, vol='Garch', p=p, q=q)
            result = model.fit(disp='off')

            # 获取条件波动率
            volatility = result.conditional_volatility / 100

            return volatility

        except ImportError:
            logger.error("arch package not installed. Install: pip install arch")
            # 返回简单滚动标准差
            return returns.rolling(window=20).std()
