"""
Trainer Facade for AgroTwin-AI.
Exposes multi-scale training pipeline, target and feature constants,
and backwards compatibility functions.
"""

from typing import Dict, Any, Callable, Optional
import pandas as pd

from src.core.training.trainer import MultiScaleTrainer, train_models_pipeline
from src.core.features.schema import get_default_feature_schema
from src.core.metrics import calculate_nse, calculate_rmse, calculate_mae, calculate_r2, calculate_pbias

FEATURE_COLS = get_default_feature_schema(mode="direct").feature_names
TARGET_COL = "monthly_runoff_mm"

MODEL_NAMES = [
    "Random Forest Regressor",
    "XGBoost Regressor",
    "Support Vector Regression (SVR)",
    "CNN-LSTM Hybrid",
    "LSTM Autoencoder + Random Forest"
]


def train_pipeline(
    epochs: int = 25,
    batch_size: int = 32,
    lr: float = 0.001,
    dropout: float = 0.25,
    k_folds: int = 5,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Dict[str, Any]:
    """
    Backwards-compatible wrapper calling the new MultiScaleTrainer.
    """
    trainer = MultiScaleTrainer(
        target_name="monthly_runoff_mm",
        learning_mode="direct",
        validation_strategy="temporal",
        fast_dev_mode=(epochs < 15)
    )
    from src.core.dataset_generator import get_dataset
    df = get_dataset()
    res = trainer.train(df, progress_callback=progress_callback)

    return {
        "best_model_name": res["champion_model_name"],
        "best_r2_score": res["champion_metrics"].get("r2", 0.0),
        "results": {
            name: {
                "r2": data["metrics"]["r2"],
                "rmse": data["metrics"]["rmse"],
                "mae": data["metrics"]["mae"],
                "nse": data["metrics"].get("nse", 0.0),
                "pbias": data["metrics"].get("pbias", 0.0),
                "y_true": data["y_true"],
                "y_pred": data["y_pred"]
            }
            for name, data in res["results"].items()
        },
        "history": res["history"]
    }
