"""
Multi-Scale Model Trainer for AgroTwin-AI.
Orchestrates training of 3 Traditional + 2 Hybrid models.
Prevents data leakage, handles Direct & Residual learning modes,
and generates complete exportable Artifact Bundles for each model.
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
import numpy as np
import pandas as pd

from src.core.features.schema import (
    ModelFeatureSchema,
    get_default_feature_schema,
    get_target_schema,
    TargetSchema
)
from src.core.features.preprocessor import MultiScaleDataPreprocessor
from src.core.features.sequences import build_grouped_temporal_sequences
from src.core.models.traditional import RandomForestModel, XGBoostModel, SVRModel
from src.core.training.splitters import get_three_way_split
from src.core.training.residual import corrected_flow, sequence_evaluation, validation_winner
from src.core.metrics import compute_all_metrics, calculate_rmse
from src.core.inference.bundle import ModelBundle, promote_to_champion

HISTORY_PATH = str(Path(__file__).resolve().parents[3] / "history.json")


class MultiScaleTrainer:
    """
    Coordinates training, validation, metric evaluation, and artifact bundling.
    Uses three partitions and selects the champion by VALIDATION RMSE.
    """

    def __init__(
        self,
        target_name: str = "monthly_runoff_mm",
        learning_mode: str = "direct",  # 'direct' or 'residual'
        validation_strategy: str = "temporal",  # 'temporal' or 'watershed'
        holdout_watershed: Optional[str] = None,
        val_ratio: float = 0.15,
        test_ratio: float = 0.20,
        random_seed: int = 42,
        fast_dev_mode: bool = False,
        tune_hyperparameters: bool = False,
        sequence_length: int = 6,
        artifact_base_dir: str = "artifacts",
        schema: Optional[ModelFeatureSchema] = None,
        dataset_metadata: Optional[Dict[str, Any]] = None,
    ):
        self.target_name = target_name
        self.learning_mode = learning_mode
        self.validation_strategy = validation_strategy
        self.holdout_watershed = holdout_watershed
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.random_seed = random_seed
        self.fast_dev_mode = fast_dev_mode
        self.tune_hyperparameters = tune_hyperparameters
        self.sequence_length = 3 if fast_dev_mode else sequence_length
        self.artifact_base_dir = artifact_base_dir
        self.dataset_metadata = dict(dataset_metadata or {})

        self.target_schema: TargetSchema = get_target_schema(target_name)
        self.schema: ModelFeatureSchema = schema or get_default_feature_schema(
            mode=learning_mode,
            include_baseline=(learning_mode == "residual"),
            target_name=target_name
        )
        if self.target_name in self.schema.feature_names:
            raise ValueError(f"Target '{self.target_name}' cannot also be used as a feature.")

    def _tune_traditional_model(
        self,
        model_key: str,
        X_tr: np.ndarray,
        y_tr: np.ndarray,
        X_v: np.ndarray,
        y_v: np.ndarray,
        val_baseline: np.ndarray,
    ) -> Any:
        """Lightweight validation-based hyperparameter tuning on TRAIN + VAL."""
        best_model = None
        best_rmse = float("inf")

        if model_key == "random_forest":
            param_grid = [
                {"n_estimators": 50, "max_depth": 8},
                {"n_estimators": 100, "max_depth": 15},
                {"n_estimators": 100, "max_depth": None}
            ]
            for p in param_grid:
                m = RandomForestModel(n_estimators=p["n_estimators"], max_depth=p["max_depth"], random_state=self.random_seed)
                m.fit(X_tr, y_tr)
                preds = m.predict(X_v)
                rmse = calculate_rmse(y_v + val_baseline, corrected_flow(val_baseline, preds))
                if rmse < best_rmse:
                    best_rmse = rmse
                    best_model = m
            return best_model

        elif model_key == "xgboost":
            param_grid = [
                {"n_estimators": 50, "learning_rate": 0.05, "max_depth": 4},
                {"n_estimators": 100, "learning_rate": 0.1, "max_depth": 6}
            ]
            for p in param_grid:
                m = XGBoostModel(n_estimators=p["n_estimators"], learning_rate=p["learning_rate"], max_depth=p["max_depth"], random_state=self.random_seed)
                m.fit(X_tr, y_tr)
                preds = m.predict(X_v)
                rmse = calculate_rmse(y_v + val_baseline, corrected_flow(val_baseline, preds))
                if rmse < best_rmse:
                    best_rmse = rmse
                    best_model = m
            return best_model

        elif model_key == "svr":
            param_grid = [
                {"C": 1.0, "epsilon": 0.1},
                {"C": 10.0, "epsilon": 0.1},
                {"C": 50.0, "epsilon": 0.05}
            ]
            for p in param_grid:
                m = SVRModel(C=p["C"], epsilon=p["epsilon"])
                m.fit(X_tr, y_tr)
                preds = m.predict(X_v)
                rmse = calculate_rmse(y_v + val_baseline, corrected_flow(val_baseline, preds))
                if rmse < best_rmse:
                    best_rmse = rmse
                    best_model = m
            return best_model

        return None

    def train(
        self,
        df: pd.DataFrame,
        selected_models: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes end-to-end training and evaluation on input DataFrame.
        """
        start_time = time.time()

        # 0. Check seasonal crop yield aggregation (P0.5)
        working_df = df.copy()
        if not self.dataset_metadata:
            is_synthetic = bool(working_df["is_synthetic"].all()) if "is_synthetic" in working_df.columns else True
            self.dataset_metadata = {
                "dataset_id": "synthetic-development-dataset" if is_synthetic else "unclassified-dataset",
                "dataset_version": "v1.0-synthetic-cornbelt" if is_synthetic else "unclassified",
                "source_kind": "synthetic_demo" if is_synthetic else "unknown",
                "is_synthetic_training_data": is_synthetic,
                "artifact_classification": "SYNTHETIC_DEVELOPMENT_ARTIFACT" if is_synthetic else "UNCLASSIFIED_SIMULATION_ARTIFACT",
                "origin": "Plant-to-Watershed synthetic development generator" if is_synthetic else "Unclassified dataset",
            }
        if self.target_name == "maize_yield_t_ha" and "seasonal_precip_mm" not in working_df.columns:
            from src.core.datasets.yield_dataset import build_seasonal_yield_dataset
            working_df = build_seasonal_yield_dataset(working_df)

        # 1. Validation split: Strict 3-way partition (Train, Val, Test) (P0.3)
        train_idx, val_idx, test_idx, split_meta = get_three_way_split(
            working_df,
            strategy=self.validation_strategy,
            val_ratio=self.val_ratio,
            test_ratio=self.test_ratio,
            holdout_watershed=self.holdout_watershed
        )

        # Splitters return DataFrame index labels, not positional offsets.
        train_df = working_df.loc[train_idx].copy()
        val_df = working_df.loc[val_idx].copy()
        test_df = working_df.loc[test_idx].copy()

        split_desc = (
            f"3-Way Leak-Free ({split_meta.get('strategy', self.validation_strategy)}): "
            f"Train={len(train_idx)}, Val={len(val_idx)}, Test={len(test_idx)}"
        )

        # 2. Extract targets
        if self.target_name not in working_df.columns:
            raise KeyError(f"Target column '{self.target_name}' not found in dataset.")

        y_train_raw = train_df[self.target_name].values.astype(np.float64)
        y_val_raw = val_df[self.target_name].values.astype(np.float64)
        y_test_raw = test_df[self.target_name].values.astype(np.float64)

        baseline_col = self.target_schema.get_baseline_col()

        # Handle Mode B: Residual Correction
        if self.learning_mode == "residual":
            if baseline_col is None or baseline_col not in working_df.columns:
                raise ValueError(f"Baseline column '{baseline_col}' missing for residual mode.")
            train_baseline = train_df[baseline_col].values.astype(np.float64)
            val_baseline = val_df[baseline_col].values.astype(np.float64)
            test_baseline = test_df[baseline_col].values.astype(np.float64)

            y_train = y_train_raw - train_baseline
            y_val = y_val_raw - val_baseline
            y_test = y_test_raw - test_baseline
        else:
            train_baseline = np.zeros(len(train_df))
            val_baseline = np.zeros(len(val_df))
            test_baseline = np.zeros(len(test_df))
            y_train = y_train_raw
            y_val = y_val_raw
            y_test = y_test_raw

        # 3. Fit Preprocessor ONLY on training data (Zero Data Leakage)
        preprocessor = MultiScaleDataPreprocessor(schema=self.schema, scale_features=True)
        preprocessor.fit(train_df)

        X_train_scaled = preprocessor.transform(train_df)
        X_val_scaled = preprocessor.transform(val_df)
        X_test_scaled = preprocessor.transform(test_df)

        # 4. Prepare 3D Temporal Sequences for Deep Learning Models (P0.1)
        has_sequences = False
        X_tr_seq, y_tr_seq, meta_tr = None, None, None
        X_val_seq, y_val_seq, meta_val = None, None, None
        X_test_seq, y_test_seq, meta_test = None, None, None

        if "watershed_id" in working_df.columns and "hru_id" in working_df.columns and "date" in working_df.columns:
            try:
                tr_work = train_df.copy()
                tr_work[self.schema.feature_names] = X_train_scaled
                tr_work["_tgt_seq"] = y_train
                tr_work["_physical_baseline_seq"] = train_baseline

                v_work = val_df.copy()
                v_work[self.schema.feature_names] = X_val_scaled
                v_work["_tgt_seq"] = y_val
                v_work["_physical_baseline_seq"] = val_baseline

                te_work = test_df.copy()
                te_work[self.schema.feature_names] = X_test_scaled
                te_work["_tgt_seq"] = y_test
                te_work["_physical_baseline_seq"] = test_baseline

                X_tr_seq, y_tr_seq, meta_tr = build_grouped_temporal_sequences(
                    tr_work, self.schema.feature_names, "_tgt_seq",
                    sequence_length=self.sequence_length, baseline_col="_physical_baseline_seq"
                )
                X_val_seq, y_val_seq, meta_val = build_grouped_temporal_sequences(
                    v_work, self.schema.feature_names, "_tgt_seq",
                    sequence_length=self.sequence_length, baseline_col="_physical_baseline_seq"
                )
                X_test_seq, y_test_seq, meta_test = build_grouped_temporal_sequences(
                    te_work, self.schema.feature_names, "_tgt_seq",
                    sequence_length=self.sequence_length, baseline_col="_physical_baseline_seq"
                )
                if len(X_tr_seq) > 0 and len(X_test_seq) > 0:
                    has_sequences = True
            except Exception:
                has_sequences = False

        # 5. Model Catalog
        rf_trees = 35 if self.fast_dev_mode else 100
        xgb_trees = 35 if self.fast_dev_mode else 100
        epochs = 6 if self.fast_dev_mode else 20
        batch_size = 32

        def cnn_model():
            from src.core.models.deep_learning import CNNLSTMModel
            return CNNLSTMModel(timesteps=self.sequence_length if has_sequences else 1,
                                n_features=X_train_scaled.shape[1], lr=0.001)

        def hybrid_model():
            from src.core.models.hybrid_ae_rf import LSTMAERandomForestModel
            return LSTMAERandomForestModel(timesteps=self.sequence_length if has_sequences else 1,
                n_features=X_train_scaled.shape[1], latent_dim=6,
                n_estimators=rf_trees, random_state=self.random_seed)

        model_catalog = {
            "Random Forest Regressor": (
                "random_forest",
                "traditional",
                lambda: RandomForestModel(n_estimators=rf_trees, random_state=self.random_seed)
            ),
            "XGBoost Regressor": (
                "xgboost",
                "traditional",
                lambda: XGBoostModel(n_estimators=xgb_trees, random_state=self.random_seed)
            ),
            "Support Vector Regression (SVR)": (
                "svr",
                "traditional",
                lambda: SVRModel(C=10.0, epsilon=0.1)
            ),
            "CNN-LSTM Hybrid": (
                "cnn_lstm",
                "sequence",
                cnn_model
            ),
            "LSTM Autoencoder + Random Forest": (
                "lstm_ae_rf",
                "sequence",
                hybrid_model
            )
        }

        # Filter by selected models
        models_to_run = {}
        if selected_models:
            for name, item in model_catalog.items():
                if any(sm.lower() in name.lower() for sm in selected_models):
                    models_to_run[name] = item
        if not models_to_run:
            models_to_run = model_catalog

        results: Dict[str, Any] = {}
        bundles: Dict[str, ModelBundle] = {}
        total_models = len(models_to_run)

        # 6. Training Loop
        for step, (display_name, (folder_name, model_category, factory)) in enumerate(models_to_run.items()):
            default_inst = factory()
            if progress_callback:
                progress_callback(step / total_models, f"Entrenando {display_name}...")

            is_seq = (model_category == "sequence" and has_sequences)

            if is_seq:
                X_tr_in, y_tr_in = X_tr_seq, y_tr_seq
                X_v_in, y_v_in = X_val_seq, y_val_seq
                X_te_in = X_test_seq
                y_true_eval, te_baseline = sequence_evaluation(meta_test, self.learning_mode)
                y_val_eval, v_baseline = sequence_evaluation(meta_val, self.learning_mode)
                model_inst = default_inst
            else:
                X_tr_in, y_tr_in = X_train_scaled, y_train
                X_v_in, y_v_in = X_val_scaled, y_val
                X_te_in = X_test_scaled
                y_true_eval = y_test_raw
                te_baseline = test_baseline
                y_val_eval, v_baseline = y_val_raw, val_baseline

                # Apply Hyperparameter Tuning if enabled (P1.1)
                if self.tune_hyperparameters and not self.fast_dev_mode and model_category == "traditional":
                    tuned_inst = self._tune_traditional_model(folder_name, X_tr_in, y_tr_in, X_v_in, y_v_in, val_baseline)
                    model_inst = tuned_inst if tuned_inst is not None else default_inst
                else:
                    model_inst = default_inst

            # Fit model
            model_inst.fit(
                X_tr_in,
                y_tr_in,
                X_val=X_v_in,
                y_val=y_v_in,
                epochs=epochs,
                batch_size=batch_size,
                verbose=0
            )

            # Generate predictions on held-out TEST set
            raw_test_preds = model_inst.predict(X_te_in)
            raw_test_preds = np.asarray(raw_test_preds, dtype=np.float64).flatten()

            # Mode transformation (Direct vs Residual)
            if self.learning_mode == "residual":
                final_test_preds = corrected_flow(te_baseline, raw_test_preds)
            else:
                final_test_preds = np.maximum(0.0, raw_test_preds)

            # Compute hydrological & agronomic metrics on TEST partition
            metrics = compute_all_metrics(
                y_true=y_true_eval,
                y_pred=final_test_preds,
                target_type=self.target_schema.target_type
            )

            # Also evaluate on VAL partition for provenance tracking
            raw_val_preds = np.asarray(model_inst.predict(X_v_in), dtype=np.float64).flatten()
            if self.learning_mode == "residual":
                final_val_preds = corrected_flow(v_baseline, raw_val_preds)
            else:
                final_val_preds = np.maximum(0.0, raw_val_preds)

            val_metrics = compute_all_metrics(
                y_true=y_val_eval,
                y_pred=final_val_preds,
                target_type=self.target_schema.target_type
            )

            # Create artifact bundle directory
            model_artifact_dir = os.path.join(
                self.artifact_base_dir,
                self.target_name,
                folder_name
            )

            bundle_metrics = dict(metrics)
            bundle_metrics["val_rmse"] = val_metrics["rmse"]
            bundle_metrics["val_mae"] = val_metrics["mae"]

            bundle = ModelBundle.save_bundle(
                artifact_dir=model_artifact_dir,
                model=model_inst,
                preprocessor=preprocessor,
                schema=self.schema,
                target_name=self.target_name,
                learning_mode=self.learning_mode,
                metrics=bundle_metrics,
                validation_strategy=self.validation_strategy,
                train_split_desc=split_desc,
                random_seed=self.random_seed,
                dataset_metadata=self.dataset_metadata,
            )

            bundles[display_name] = bundle
            results[display_name] = {
                "folder": folder_name,
                "metrics": metrics,
                "val_metrics": val_metrics,
                "selection_rmse": calculate_rmse(y_val_eval, final_val_preds),
                "y_true": y_true_eval.tolist(),
                "y_pred": final_test_preds.tolist(),
                "artifact_dir": model_artifact_dir
            }

        # 7. Selection uses VALIDATION only; TEST metrics remain diagnostics.
        scores = {name: res["selection_rmse"] for name, res in results.items()}
        champion_name = validation_winner(scores)
        ranking_records = [{"model_name": name, "selection_partition": "VALIDATION",
            "rmse": scores[name], "metrics": results[name]["val_metrics"]}
            for name in sorted(scores, key=lambda name: (scores[name], name))]
        champion_folder = results[champion_name]["folder"]

        # Promote to champion directory: artifacts/<target_name>/champion/
        champ_dir = promote_to_champion(
            target_name=self.target_name,
            model_folder=champion_folder,
            base_artifact_dir=self.artifact_base_dir
        )

        total_elapsed = round(time.time() - start_time, 2)

        if progress_callback:
            progress_callback(1.0, f"¡Entrenamiento completado en {total_elapsed}s! Campeón: {champion_name}")

        # 8. Update history.json for persistence and dashboarding
        history_payload = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "target_name": self.target_name,
            "learning_mode": self.learning_mode,
            "validation_strategy": self.validation_strategy,
            "split_description": split_desc,
            "champion_model_name": champion_name,
            "champion_metrics": results[champion_name]["val_metrics"],
            "champion_test_metrics": results[champion_name]["metrics"],
            "selection_partition": "VALIDATION",
            "champion_artifact_dir": champ_dir,
            "ranking_records": ranking_records,
            "duration_seconds": total_elapsed,
            "is_synthetic_dataset": bool(self.dataset_metadata.get("is_synthetic_training_data", False)),
            "dataset_id": self.dataset_metadata.get("dataset_id"),
            "dataset_source_kind": self.dataset_metadata.get("source_kind"),
            "artifact_classification": self.dataset_metadata.get("artifact_classification"),
            "models": {k: v["metrics"] for k, v in results.items()},
            "train_samples": len(train_idx),
            "val_samples": len(val_idx),
            "test_samples": len(test_idx)
        }

        os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(history_payload, f, indent=2)

        return {
            "champion_model_name": champion_name,
            "champion_metrics": results[champion_name]["val_metrics"],
            "champion_test_metrics": results[champion_name]["metrics"],
            "selection_partition": "VALIDATION",
            "champion_dir": champ_dir,
            "ranking_records": ranking_records,
            "results": results,
            "split_description": split_desc,
            "duration_seconds": total_elapsed,
            "history": history_payload
        }


def train_models_pipeline(
    df: Optional[pd.DataFrame] = None,
    target_name: str = "monthly_runoff_mm",
    learning_mode: str = "direct",
    validation_strategy: str = "temporal",
    fast_dev_mode: bool = False,
    tune_hyperparameters: bool = False,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    schema: Optional[ModelFeatureSchema] = None,
    dataset_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Convenience function to run training pipeline.
    If df is None, loads default dataset.
    """
    from src.core.dataset_generator import get_dataset
    if df is None:
        df = get_dataset()

    trainer = MultiScaleTrainer(
        target_name=target_name,
        learning_mode=learning_mode,
        validation_strategy=validation_strategy,
        fast_dev_mode=fast_dev_mode,
        tune_hyperparameters=tune_hyperparameters,
        schema=schema,
        dataset_metadata=dataset_metadata,
    )
    return trainer.train(df, progress_callback=progress_callback)
