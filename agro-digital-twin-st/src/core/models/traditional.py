"""
Traditional ML Regression Models for AgroTwin-AI:
1. Random Forest Regressor
2. XGBoost Regressor
3. Support Vector Regression (SVR)
"""

import os
import joblib
from typing import Dict, Any, Optional
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.svm import SVR
import xgboost as xgb

from .base import BaseMultiScaleModel


class RandomForestModel(BaseMultiScaleModel):
    """Random Forest Regressor wrapper."""

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: Optional[int] = 12,
        min_samples_split: int = 4,
        random_state: int = 42,
        n_jobs: int = -1
    ):
        super().__init__(name="Random Forest Regressor", model_type="traditional")
        self.params = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "min_samples_split": min_samples_split,
            "random_state": random_state,
            "n_jobs": n_jobs
        }
        self.estimator = RandomForestRegressor(**self.params)

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        epochs: int = 25,
        batch_size: int = 32,
        verbose: int = 0
    ) -> "RandomForestModel":
        self.estimator.fit(X_train, y_train)
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.estimator.predict(X)

    def save(self, artifact_dir: str) -> str:
        os.makedirs(artifact_dir, exist_ok=True)
        model_file = os.path.join(artifact_dir, "model.joblib")
        joblib.dump({
            "name": self.name,
            "model_type": self.model_type,
            "params": self.params,
            "estimator": self.estimator,
            "is_fitted": self.is_fitted
        }, model_file)
        return model_file

    @classmethod
    def load(cls, artifact_dir: str) -> "RandomForestModel":
        model_file = os.path.join(artifact_dir, "model.joblib")
        data = joblib.load(model_file)
        instance = cls(**data.get("params", {}))
        instance.estimator = data["estimator"]
        instance.is_fitted = data["is_fitted"]
        return instance


class XGBoostModel(BaseMultiScaleModel):
    """XGBoost Regressor wrapper."""

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 6,
        learning_rate: float = 0.08,
        subsample: float = 0.85,
        colsample_bytree: float = 0.85,
        random_state: int = 42,
        n_jobs: int = -1
    ):
        super().__init__(name="XGBoost Regressor", model_type="traditional")
        self.params = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "learning_rate": learning_rate,
            "subsample": subsample,
            "colsample_bytree": colsample_bytree,
            "random_state": random_state,
            "n_jobs": n_jobs
        }
        self.estimator = xgb.XGBRegressor(**self.params)

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        epochs: int = 25,
        batch_size: int = 32,
        verbose: int = 0
    ) -> "XGBoostModel":
        eval_set = [(X_val, y_val)] if (X_val is not None and y_val is not None) else None
        self.estimator.fit(
            X_train,
            y_train,
            eval_set=eval_set,
            verbose=False
        )
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.estimator.predict(X)

    def save(self, artifact_dir: str) -> str:
        os.makedirs(artifact_dir, exist_ok=True)
        model_file = os.path.join(artifact_dir, "model.joblib")
        joblib.dump({
            "name": self.name,
            "model_type": self.model_type,
            "params": self.params,
            "estimator": self.estimator,
            "is_fitted": self.is_fitted
        }, model_file)
        return model_file

    @classmethod
    def load(cls, artifact_dir: str) -> "XGBoostModel":
        model_file = os.path.join(artifact_dir, "model.joblib")
        data = joblib.load(model_file)
        instance = cls(**data.get("params", {}))
        instance.estimator = data["estimator"]
        instance.is_fitted = data["is_fitted"]
        return instance


class SVRModel(BaseMultiScaleModel):
    """Support Vector Regression (SVR) wrapper."""

    def __init__(
        self,
        kernel: str = "rbf",
        C: float = 10.0,
        epsilon: float = 0.1,
        gamma: str = "scale"
    ):
        super().__init__(name="Support Vector Regression (SVR)", model_type="traditional")
        self.params = {
            "kernel": kernel,
            "C": C,
            "epsilon": epsilon,
            "gamma": gamma
        }
        self.estimator = SVR(**self.params)

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        epochs: int = 25,
        batch_size: int = 32,
        verbose: int = 0
    ) -> "SVRModel":
        self.estimator.fit(X_train, y_train)
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.estimator.predict(X)

    def save(self, artifact_dir: str) -> str:
        os.makedirs(artifact_dir, exist_ok=True)
        model_file = os.path.join(artifact_dir, "model.joblib")
        joblib.dump({
            "name": self.name,
            "model_type": self.model_type,
            "params": self.params,
            "estimator": self.estimator,
            "is_fitted": self.is_fitted
        }, model_file)
        return model_file

    @classmethod
    def load(cls, artifact_dir: str) -> "SVRModel":
        model_file = os.path.join(artifact_dir, "model.joblib")
        data = joblib.load(model_file)
        instance = cls(**data.get("params", {}))
        instance.estimator = data["estimator"]
        instance.is_fitted = data["is_fitted"]
        return instance
