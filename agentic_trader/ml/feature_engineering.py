"""特征工程 - 为机器学习模型提取特征"""

import logging
import numpy as np
import pandas as pd
import talib
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    特征工程器

    从原始市场数据中提取机器学习特征
    """

    def __init__(self):
        """初始化特征工程器"""
        self.feature_columns = []

    def create_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        创建完整的特征集

        Args:
            data: 包含OHLCV的DataFrame

        Returns:
            包含所有特征的DataFrame
        """
        if len(data) < 50:
            logger.warning("Data length too short for feature engineering")
            return data

        df = data.copy()

        # 1. 价格特征
        df = self._add_price_features(df)

        # 2. 技术指标特征
        df = self._add_technical_indicators(df)

        # 3. 统计特征
        df = self._add_statistical_features(df)

        # 4. 时间特征
        df = self._add_time_features(df)

        # 5. 成交量特征
        df = self._add_volume_features(df)

        # 6. 波动率特征
        df = self._add_volatility_features(df)

        # 7. 动量特征
        df = self._add_momentum_features(df)

        # 删除包含NaN的行
        df = df.dropna()

        # 记录特征列
        self.feature_columns = [col for col in df.columns
                               if col not in ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']]

        logger.info(f"Created {len(self.feature_columns)} features")

        return df

    def _add_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加价格相关特征"""
        close = df['close']
        high = df['high']
        low = df['low']
        open_ = df['open']

        # 价格变化
        df['price_change'] = close.pct_change()
        df['price_change_5'] = close.pct_change(5)
        df['price_change_10'] = close.pct_change(10)

        # 高低价差
        df['high_low_pct'] = (high - low) / close

        # 开盘价与收盘价差
        df['open_close_pct'] = (close - open_) / open_

        # 价格位置（相对于高低价）
        df['close_position'] = (close - low) / (high - low + 1e-10)

        # 对数收益率
        df['log_return'] = np.log(close / close.shift(1))

        return df

    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加技术指标特征"""
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        volume = df['volume'].values

        # RSI
        df['rsi_14'] = talib.RSI(close, timeperiod=14)
        df['rsi_7'] = talib.RSI(close, timeperiod=7)
        df['rsi_21'] = talib.RSI(close, timeperiod=21)

        # MACD
        macd, signal, hist = talib.MACD(close)
        df['macd'] = macd
        df['macd_signal'] = signal
        df['macd_hist'] = hist

        # 布林带
        upper, middle, lower = talib.BBANDS(close, timeperiod=20)
        df['bb_upper'] = upper
        df['bb_middle'] = middle
        df['bb_lower'] = lower
        df['bb_width'] = (upper - lower) / middle
        df['bb_position'] = (close - lower) / (upper - lower + 1e-10)

        # 均线
        df['sma_5'] = talib.SMA(close, timeperiod=5)
        df['sma_10'] = talib.SMA(close, timeperiod=10)
        df['sma_20'] = talib.SMA(close, timeperiod=20)
        df['sma_50'] = talib.SMA(close, timeperiod=50)

        df['ema_5'] = talib.EMA(close, timeperiod=5)
        df['ema_10'] = talib.EMA(close, timeperiod=10)
        df['ema_20'] = talib.EMA(close, timeperiod=20)

        # 均线距离
        df['sma_5_dist'] = (close - df['sma_5']) / df['sma_5']
        df['sma_20_dist'] = (close - df['sma_20']) / df['sma_20']

        # ATR（平均真实波幅）
        df['atr_14'] = talib.ATR(high, low, close, timeperiod=14)
        df['atr_pct'] = df['atr_14'] / close

        # ADX（趋势强度）
        df['adx_14'] = talib.ADX(high, low, close, timeperiod=14)

        # CCI（商品通道指数）
        df['cci_14'] = talib.CCI(high, low, close, timeperiod=14)

        # 随机指标
        slowk, slowd = talib.STOCH(high, low, close)
        df['stoch_k'] = slowk
        df['stoch_d'] = slowd

        # OBV（能量潮）
        df['obv'] = talib.OBV(close, volume)
        df['obv_sma'] = df['obv'].rolling(window=20).mean()

        return df

    def _add_statistical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加统计特征"""
        close = df['close']

        # 滚动统计
        for window in [5, 10, 20]:
            df[f'mean_{window}'] = close.rolling(window=window).mean()
            df[f'std_{window}'] = close.rolling(window=window).std()
            df[f'min_{window}'] = close.rolling(window=window).min()
            df[f'max_{window}'] = close.rolling(window=window).max()

            # 标准化价格位置
            df[f'normalized_pos_{window}'] = (
                (close - df[f'min_{window}']) /
                (df[f'max_{window}'] - df[f'min_{window}'] + 1e-10)
            )

        # 偏度和峰度
        df['skew_20'] = close.rolling(window=20).skew()
        df['kurt_20'] = close.rolling(window=20).kurt()

        return df

    def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加时间特征"""
        if 'timestamp' in df.columns:
            df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
            df['minute'] = pd.to_datetime(df['timestamp']).dt.minute
            df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.dayofweek

            # 市场时段（IST时间）
            # 9:15-11:00 开盘时段
            # 11:00-14:00 中段
            # 14:00-15:30 收盘时段
            df['is_opening_session'] = ((df['hour'] == 9) |
                                       ((df['hour'] == 10) & (df['minute'] <= 59)))
            df['is_closing_session'] = ((df['hour'] >= 14))

        return df

    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加成交量特征"""
        volume = df['volume']

        # 成交量变化
        df['volume_change'] = volume.pct_change()
        df['volume_ma_5'] = volume.rolling(window=5).mean()
        df['volume_ma_20'] = volume.rolling(window=20).mean()

        # 相对成交量
        df['volume_ratio'] = volume / df['volume_ma_20']

        # 成交量标准化
        df['volume_std_20'] = volume.rolling(window=20).std()
        df['volume_zscore'] = (volume - df['volume_ma_20']) / (df['volume_std_20'] + 1e-10)

        # 价量关系
        df['price_volume_corr'] = (
            df['close'].rolling(window=20).corr(df['volume'])
        )

        return df

    def _add_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加波动率特征"""
        close = df['close']

        # 历史波动率
        returns = close.pct_change()
        for window in [5, 10, 20]:
            df[f'volatility_{window}'] = returns.rolling(window=window).std() * np.sqrt(252)

        # Parkinson波动率（使用高低价）
        df['parkinson_vol'] = np.sqrt(
            (1 / (4 * np.log(2))) *
            np.log(df['high'] / df['low']) ** 2
        ).rolling(window=20).mean()

        # 波动率变化
        df['volatility_change'] = df['volatility_20'].pct_change()

        return df

    def _add_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加动量特征"""
        close = df['close']

        # 动量指标
        for period in [5, 10, 20]:
            df[f'momentum_{period}'] = close - close.shift(period)
            df[f'roc_{period}'] = talib.ROC(close.values, timeperiod=period)

        # Williams %R
        df['willr_14'] = talib.WILLR(df['high'].values, df['low'].values,
                                      close.values, timeperiod=14)

        # 相对强弱
        df['price_strength'] = (close - close.rolling(20).min()) / (
            close.rolling(20).max() - close.rolling(20).min() + 1e-10
        )

        return df

    def get_feature_importance_names(self) -> List[str]:
        """获取特征名称列表"""
        return self.feature_columns

    def create_target(self, df: pd.DataFrame, horizon: int = 1,
                     target_type: str = 'return') -> pd.Series:
        """
        创建预测目标

        Args:
            df: 数据DataFrame
            horizon: 预测时间窗口
            target_type: 目标类型 ('return', 'direction', 'volatility')

        Returns:
            目标序列
        """
        close = df['close']

        if target_type == 'return':
            # 未来收益率
            target = close.shift(-horizon).pct_change()

        elif target_type == 'direction':
            # 未来价格方向（1=上涨，0=下跌）
            future_return = close.shift(-horizon) / close - 1
            target = (future_return > 0).astype(int)

        elif target_type == 'volatility':
            # 未来波动率
            returns = close.pct_change()
            target = returns.shift(-horizon).rolling(window=horizon).std()

        else:
            raise ValueError(f"Unknown target type: {target_type}")

        return target

    def normalize_features(self, df: pd.DataFrame,
                          scaler_type: str = 'standard') -> pd.DataFrame:
        """
        标准化特征

        Args:
            df: 特征DataFrame
            scaler_type: 标准化类型 ('standard', 'minmax', 'robust')

        Returns:
            标准化后的DataFrame
        """
        from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler

        df_normalized = df.copy()

        if scaler_type == 'standard':
            scaler = StandardScaler()
        elif scaler_type == 'minmax':
            scaler = MinMaxScaler()
        elif scaler_type == 'robust':
            scaler = RobustScaler()
        else:
            raise ValueError(f"Unknown scaler type: {scaler_type}")

        # 只标准化特征列
        feature_cols = [col for col in df.columns
                       if col not in ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']]

        if feature_cols:
            df_normalized[feature_cols] = scaler.fit_transform(df[feature_cols])

        return df_normalized
