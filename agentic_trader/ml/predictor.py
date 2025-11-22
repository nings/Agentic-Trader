"""价格预测器 - 使用机器学习模型预测价格走势"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import joblib

logger = logging.getLogger(__name__)


class PricePredictor:
    """
    价格预测器

    支持多种模型：LSTM、XGBoost、LightGBM
    """

    def __init__(self, model_type: str = 'xgboost', model_path: Optional[str] = None):
        """
        初始化预测器

        Args:
            model_type: 模型类型 ('xgboost', 'lightgbm', 'lstm')
            model_path: 预训练模型路径
        """
        self.model_type = model_type
        self.model = None
        self.scaler = None
        self.feature_names = []

        if model_path and Path(model_path).exists():
            self.load_model(model_path)
        else:
            self._initialize_model()

    def _initialize_model(self):
        """初始化模型"""
        if self.model_type == 'xgboost':
            try:
                import xgboost as xgb
                self.model = xgb.XGBRegressor(
                    n_estimators=100,
                    max_depth=5,
                    learning_rate=0.05,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    random_state=42,
                    n_jobs=-1
                )
                logger.info("Initialized XGBoost model")
            except ImportError:
                logger.error("XGBoost not installed. Install: pip install xgboost")
                raise

        elif self.model_type == 'lightgbm':
            try:
                import lightgbm as lgb
                self.model = lgb.LGBMRegressor(
                    n_estimators=100,
                    max_depth=5,
                    learning_rate=0.05,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    random_state=42,
                    n_jobs=-1,
                    verbose=-1
                )
                logger.info("Initialized LightGBM model")
            except ImportError:
                logger.error("LightGBM not installed. Install: pip install lightgbm")
                raise

        elif self.model_type == 'lstm':
            self._initialize_lstm_model()

        else:
            raise ValueError(f"Unknown model type: {self.model_type}")

    def _initialize_lstm_model(self):
        """初始化LSTM模型"""
        try:
            from tensorflow import keras
            from tensorflow.keras import layers

            # 简单的LSTM架构
            self.model = keras.Sequential([
                layers.LSTM(64, return_sequences=True, input_shape=(None, 1)),
                layers.Dropout(0.2),
                layers.LSTM(32, return_sequences=False),
                layers.Dropout(0.2),
                layers.Dense(16, activation='relu'),
                layers.Dense(1)
            ])

            self.model.compile(
                optimizer='adam',
                loss='mse',
                metrics=['mae']
            )

            logger.info("Initialized LSTM model")

        except ImportError:
            logger.error("TensorFlow not installed. Install: pip install tensorflow")
            raise

    def train(self, X: pd.DataFrame, y: pd.Series,
              validation_split: float = 0.2,
              **kwargs) -> Dict[str, Any]:
        """
        训练模型

        Args:
            X: 特征数据
            y: 目标变量
            validation_split: 验证集比例
            **kwargs: 其他训练参数

        Returns:
            训练结果字典
        """
        if self.model is None:
            self._initialize_model()

        # 保存特征名称
        self.feature_names = list(X.columns)

        # 分割训练集和验证集
        split_idx = int(len(X) * (1 - validation_split))
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]

        logger.info(f"Training {self.model_type} model with {len(X_train)} samples")

        if self.model_type in ['xgboost', 'lightgbm']:
            # 训练树模型
            self.model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                verbose=False
            )

            # 评估
            train_score = self.model.score(X_train, y_train)
            val_score = self.model.score(X_val, y_val)

            # 获取特征重要性
            feature_importance = self._get_feature_importance()

            results = {
                'train_score': train_score,
                'val_score': val_score,
                'feature_importance': feature_importance,
                'model_type': self.model_type
            }

        elif self.model_type == 'lstm':
            # 准备LSTM数据
            X_train_lstm = self._prepare_lstm_data(X_train.values)
            X_val_lstm = self._prepare_lstm_data(X_val.values)

            # 训练LSTM
            history = self.model.fit(
                X_train_lstm, y_train.values,
                validation_data=(X_val_lstm, y_val.values),
                epochs=kwargs.get('epochs', 50),
                batch_size=kwargs.get('batch_size', 32),
                verbose=0
            )

            results = {
                'train_loss': history.history['loss'][-1],
                'val_loss': history.history['val_loss'][-1],
                'history': history.history,
                'model_type': self.model_type
            }

        logger.info(f"Training completed. Results: {results}")

        return results

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        预测

        Args:
            X: 特征数据

        Returns:
            预测结果
        """
        if self.model is None:
            raise ValueError("Model not trained or loaded")

        if self.model_type in ['xgboost', 'lightgbm']:
            predictions = self.model.predict(X)

        elif self.model_type == 'lstm':
            X_lstm = self._prepare_lstm_data(X.values)
            predictions = self.model.predict(X_lstm, verbose=0).flatten()

        return predictions

    def predict_direction(self, X: pd.DataFrame, threshold: float = 0.0) -> np.ndarray:
        """
        预测价格方向

        Args:
            X: 特征数据
            threshold: 分类阈值

        Returns:
            方向预测 (1=上涨, 0=下跌)
        """
        predictions = self.predict(X)
        return (predictions > threshold).astype(int)

    def predict_with_confidence(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        预测并返回置信度

        Args:
            X: 特征数据

        Returns:
            (预测值, 置信度)
        """
        predictions = self.predict(X)

        # 简单的置信度估计（可以改进）
        if self.model_type in ['xgboost', 'lightgbm']:
            # 使用多棵树的标准差作为置信度
            try:
                # 获取所有树的预测
                tree_predictions = np.array([
                    tree.predict(X) for tree in self.model.estimators_
                ])
                confidence = 1.0 / (1.0 + tree_predictions.std(axis=0))
            except:
                # 如果无法获取树预测，使用默认置信度
                confidence = np.ones_like(predictions) * 0.5

        else:
            # LSTM使用固定置信度
            confidence = np.ones_like(predictions) * 0.7

        return predictions, confidence

    def _prepare_lstm_data(self, data: np.ndarray, sequence_length: int = 10) -> np.ndarray:
        """
        准备LSTM输入数据

        Args:
            data: 原始数据
            sequence_length: 序列长度

        Returns:
            LSTM格式的数据
        """
        sequences = []
        for i in range(len(data) - sequence_length + 1):
            sequences.append(data[i:i + sequence_length])

        return np.array(sequences)

    def _get_feature_importance(self) -> Dict[str, float]:
        """获取特征重要性"""
        if self.model_type in ['xgboost', 'lightgbm']:
            importance = self.model.feature_importances_
            feature_importance = dict(zip(self.feature_names, importance))

            # 排序
            feature_importance = dict(
                sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
            )

            return feature_importance

        return {}

    def get_top_features(self, n: int = 10) -> List[Tuple[str, float]]:
        """
        获取最重要的N个特征

        Args:
            n: 返回特征数量

        Returns:
            [(特征名, 重要性), ...]
        """
        importance = self._get_feature_importance()
        return list(importance.items())[:n]

    def save_model(self, path: str):
        """
        保存模型

        Args:
            path: 保存路径
        """
        model_data = {
            'model': self.model,
            'model_type': self.model_type,
            'feature_names': self.feature_names,
            'scaler': self.scaler
        }

        joblib.dump(model_data, path)
        logger.info(f"Model saved to {path}")

    def load_model(self, path: str):
        """
        加载模型

        Args:
            path: 模型路径
        """
        model_data = joblib.load(path)

        self.model = model_data['model']
        self.model_type = model_data['model_type']
        self.feature_names = model_data.get('feature_names', [])
        self.scaler = model_data.get('scaler')

        logger.info(f"Model loaded from {path}")

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """
        评估模型性能

        Args:
            X: 特征数据
            y: 真实标签

        Returns:
            评估指标
        """
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

        predictions = self.predict(X)

        metrics = {
            'mse': mean_squared_error(y, predictions),
            'rmse': np.sqrt(mean_squared_error(y, predictions)),
            'mae': mean_absolute_error(y, predictions),
            'r2': r2_score(y, predictions)
        }

        # 方向准确率
        direction_true = (y > 0).astype(int)
        direction_pred = (predictions > 0).astype(int)
        metrics['direction_accuracy'] = (direction_true == direction_pred).mean()

        logger.info(f"Evaluation metrics: {metrics}")

        return metrics


class EnsemblePredictor:
    """
    集成预测器

    组合多个模型的预测结果
    """

    def __init__(self, models: List[PricePredictor], weights: Optional[List[float]] = None):
        """
        初始化集成预测器

        Args:
            models: 模型列表
            weights: 模型权重（可选）
        """
        self.models = models
        self.weights = weights or [1.0 / len(models)] * len(models)

        if len(self.weights) != len(self.models):
            raise ValueError("Number of weights must match number of models")

        # 标准化权重
        weight_sum = sum(self.weights)
        self.weights = [w / weight_sum for w in self.weights]

        logger.info(f"Initialized ensemble with {len(models)} models")

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        集成预测

        Args:
            X: 特征数据

        Returns:
            加权平均预测
        """
        predictions = []

        for model, weight in zip(self.models, self.weights):
            pred = model.predict(X)
            predictions.append(pred * weight)

        ensemble_pred = np.sum(predictions, axis=0)

        return ensemble_pred

    def predict_direction(self, X: pd.DataFrame) -> np.ndarray:
        """
        集成方向预测（投票）

        Args:
            X: 特征数据

        Returns:
            方向预测
        """
        direction_votes = []

        for model in self.models:
            direction = model.predict_direction(X)
            direction_votes.append(direction)

        # 多数投票
        direction_votes = np.array(direction_votes)
        ensemble_direction = (direction_votes.mean(axis=0) > 0.5).astype(int)

        return ensemble_direction
