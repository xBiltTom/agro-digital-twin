"""Preliminary next-day outlet-flow experiment.

The experiment uses only information available on an issue date and evaluates
on a later contiguous period.  It is intentionally small and tabular: one
South Fork year is enough to verify the pipeline, not to claim transfer to
other years, watersheds, or observed flows.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd

from src.core.features.preprocessor import MultiScaleDataPreprocessor
from src.core.features.schema import FeatureDefinition, ModelFeatureSchema
from src.core.inference.bundle import ModelBundle, promote_to_champion
from src.core.metrics import compute_all_metrics
from src.core.models.traditional import RandomForestModel, SVRModel, XGBoostModel


TARGET = "next_day_streamflow_m3s"
DEFAULT_BASE_VARIABLES = (
    "streamflow_m3s",
    "precip_mm",
    "temp_mean_c",
    "solar_radiation",
    "et_mm",
    "infiltration_mm",
)
DEFAULT_LAGS = (1, 2, 3, 7)


@dataclass(frozen=True)
class TemporalSplit:
    train_start: str
    train_end: str
    validation_start: str
    validation_end: str
    test_start: str
    test_end: str
    train_samples: int
    validation_samples: int
    test_samples: int


def _complete_base_variables(df: pd.DataFrame, candidates: Iterable[str]) -> list[str]:
    return [
        column for column in candidates
        if column in df.columns and pd.to_numeric(df[column], errors="coerce").notna().all()
    ]


def build_next_day_dataset(
    daily_df: pd.DataFrame,
    *,
    base_variables: Sequence[str] = DEFAULT_BASE_VARIABLES,
    lags: Sequence[int] = DEFAULT_LAGS,
) -> tuple[pd.DataFrame, list[str], Dict[str, Any]]:
    """Create issue-date features and a one-day-ahead target without leakage."""
    if "date" not in daily_df or "streamflow_m3s" not in daily_df:
        raise ValueError("A daily dataset must contain date and streamflow_m3s columns")
    if any(lag < 1 for lag in lags):
        raise ValueError("Lags must be positive integers")
    work = daily_df.copy()
    work["date"] = pd.to_datetime(work["date"], errors="raise").dt.normalize()
    work = work.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)
    variables = _complete_base_variables(work, base_variables)
    if "streamflow_m3s" not in variables:
        raise ValueError("streamflow_m3s must be complete to build a persistence baseline")
    result = pd.DataFrame({"issue_date": work["date"], "target_date": work["date"].shift(-1)})
    feature_names: list[str] = []
    for variable in variables:
        numeric = pd.to_numeric(work[variable], errors="coerce")
        for lag in sorted(set(lags)):
            feature_name = f"{variable}_lag_{lag}"
            # lag_1 is the value known on issue_date; larger lags are older.
            result[feature_name] = numeric.shift(lag - 1)
            feature_names.append(feature_name)
    result[TARGET] = pd.to_numeric(work["streamflow_m3s"], errors="coerce").shift(-1)
    result["streamflow_persistence_m3s"] = result["streamflow_m3s_lag_1"]
    contiguous = (result["target_date"] - result["issue_date"]) == pd.Timedelta(days=1)
    for lag in sorted(set(lags)):
        previous_date = work["date"].shift(lag - 1)
        contiguous &= (work["date"] - previous_date).fillna(pd.Timedelta(days=0)) == pd.Timedelta(days=lag - 1)
    result = result.loc[contiguous].dropna(
        subset=["issue_date", "target_date", *feature_names, TARGET]
    ).reset_index(drop=True)
    result["data_provenance"] = (
        str(work["data_provenance"].dropna().iloc[0])
        if "data_provenance" in work and work["data_provenance"].notna().any()
        else "unknown"
    )
    result["data_classification"] = (
        str(work["data_classification"].dropna().iloc[0])
        if "data_classification" in work and work["data_classification"].notna().any()
        else "unknown"
    )
    metadata = {
        "target": TARGET,
        "target_unit": "m3/s",
        "horizon": "next calendar day",
        "issue_date_semantics": "features use observations/states through issue_date only",
        "base_variables": variables,
        "lags": list(sorted(set(lags))),
        "feature_names": feature_names,
        "rows_before_dropna": int(len(work)),
        "rows_after_dropna": int(len(result)),
        "excluded_incomplete_variables": [column for column in base_variables if column not in variables],
    }
    return result, feature_names, metadata


def _date_range(frame: pd.DataFrame, column: str) -> tuple[str, str]:
    return str(frame[column].min().date()), str(frame[column].max().date())


def temporal_train_validation_test_split(
    prepared_df: pd.DataFrame,
    *,
    train_fraction: float = 0.60,
    validation_fraction: float = 0.20,
    minimum_train_samples: int = 30,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, TemporalSplit]:
    """Split contiguous issue dates in chronological order."""
    if not 0.0 < train_fraction < 1.0 or not 0.0 < validation_fraction < 1.0:
        raise ValueError("Temporal fractions must be between zero and one")
    if train_fraction + validation_fraction >= 1.0:
        raise ValueError("Train plus validation fractions must leave a test period")
    frame = prepared_df.sort_values("issue_date").reset_index(drop=True)
    n = len(frame)
    train_end = int(n * train_fraction)
    validation_end = int(n * (train_fraction + validation_fraction))
    if train_end < minimum_train_samples or validation_end <= train_end or validation_end >= n:
        raise ValueError(f"Not enough chronological samples for a three-way split: {n}")
    train = frame.iloc[:train_end].copy()
    validation = frame.iloc[train_end:validation_end].copy()
    test = frame.iloc[validation_end:].copy()
    split = TemporalSplit(
        *_date_range(train, "issue_date"),
        *_date_range(validation, "issue_date"),
        *_date_range(test, "issue_date"),
        len(train), len(validation), len(test),
    )
    return train, validation, test, split


def _experiment_schema(feature_names: Sequence[str]) -> ModelFeatureSchema:
    units = {
        "streamflow_m3s": "m3/s",
        "precip_mm": "mm/day",
        "temp_mean_c": "degC",
        "solar_radiation": "MJ/m2/day",
        "et_mm": "mm/day",
        "infiltration_mm": "mm/day",
    }
    definitions = []
    for feature_name in feature_names:
        base_name = feature_name.rsplit("_lag_", 1)[0]
        definitions.append(FeatureDefinition(
            name=feature_name,
            dtype="float",
            unit=units.get(base_name, "unknown"),
            scale_level="Watershed" if base_name == "streamflow_m3s" else "Climate/Watershed",
            required=True,
            default=None,
            description=f"{base_name} available at issue date or trailing lag",
        ))
    return ModelFeatureSchema(definitions, strict_missing=True)


class NextDayExperiment:
    """Run, evaluate, and export a reproducible preliminary experiment."""

    def __init__(
        self,
        *,
        artifact_base_dir: str,
        dataset_metadata: Dict[str, Any],
        random_seed: int = 42,
        fast_dev_mode: bool = True,
    ):
        self.artifact_base_dir = artifact_base_dir
        self.dataset_metadata = dict(dataset_metadata)
        self.random_seed = random_seed
        self.fast_dev_mode = fast_dev_mode

    def _models(self) -> Dict[str, Any]:
        trees = 35 if self.fast_dev_mode else 150
        return {
            "random_forest": RandomForestModel(n_estimators=trees, random_state=self.random_seed),
            "svr": SVRModel(C=10.0, epsilon=0.05),
            "xgboost": XGBoostModel(n_estimators=trees, random_state=self.random_seed),
        }

    def run(
        self,
        daily_df: pd.DataFrame,
        *,
        selected_models: Sequence[str] = ("random_forest", "svr"),
        base_variables: Sequence[str] = DEFAULT_BASE_VARIABLES,
        lags: Sequence[int] = DEFAULT_LAGS,
    ) -> Dict[str, Any]:
        started = time.time()
        prepared, feature_names, preparation = build_next_day_dataset(
            daily_df, base_variables=base_variables, lags=lags
        )
        train, validation, test, split = temporal_train_validation_test_split(prepared)
        schema = _experiment_schema(feature_names)
        preprocessor = MultiScaleDataPreprocessor(schema=schema, scale_features=True)
        x_train = preprocessor.fit_transform(train)
        x_validation = preprocessor.transform(validation)
        x_test = preprocessor.transform(test)
        y_train = train[TARGET].to_numpy(dtype=float)
        y_validation = validation[TARGET].to_numpy(dtype=float)
        y_test = test[TARGET].to_numpy(dtype=float)
        baseline_pred = test["streamflow_persistence_m3s"].to_numpy(dtype=float)
        results: Dict[str, Any] = {"Persistence baseline": {
            "metrics": compute_all_metrics(y_test, baseline_pred, target_type="streamflow"),
            "validation_metrics": compute_all_metrics(
                validation[TARGET], validation["streamflow_persistence_m3s"], target_type="streamflow"
            ),
            "artifact_dir": None,
            "model_version": "persistence-1",
        }}
        bundles: Dict[str, str] = {}
        model_catalog = self._models()
        for model_key in selected_models:
            if model_key not in model_catalog:
                raise ValueError(f"Unknown next-day model: {model_key}")
            model = model_catalog[model_key]
            model.fit(x_train, y_train, X_val=x_validation, y_val=y_validation, verbose=0)
            predictions = np.asarray(model.predict(x_test), dtype=float).reshape(-1)
            validation_predictions = np.asarray(model.predict(x_validation), dtype=float).reshape(-1)
            metrics = compute_all_metrics(y_test, predictions, target_type="streamflow")
            validation_metrics = compute_all_metrics(y_validation, validation_predictions, target_type="streamflow")
            model_dir = os.path.join(self.artifact_base_dir, TARGET, model_key)
            metadata = dict(self.dataset_metadata)
            metadata.update({
                "dataset_version": metadata.get("dataset_version", metadata.get("dataset_id", "unknown")),
                "experiment_status": "EXPERIMENTAL_SIMULATION_ONLY",
                "limitations": list(metadata.get("limitations", [])) + [
                    "One South Fork simulation year; no claim of observed-flow or cross-watershed generalization.",
                    "Temporal holdout evaluates a later segment of the same modeled year.",
                ],
            })
            bundle = ModelBundle.save_bundle(
                artifact_dir=model_dir,
                model=model,
                preprocessor=preprocessor,
                schema=schema,
                target_name=TARGET,
                learning_mode="direct",
                metrics={**metrics, "val_rmse": validation_metrics["rmse"], "baseline_rmse": results["Persistence baseline"]["metrics"]["rmse"]},
                validation_strategy="chronological_train_validation_test",
                train_split_desc=json.dumps(asdict(split), ensure_ascii=True),
                random_seed=self.random_seed,
                dataset_metadata=metadata,
                forecast_horizon={"steps": 1, "unit": "day", "issue_date_column": "issue_date"},
                inference_contract={
                    "required_features": feature_names,
                    "target": TARGET,
                    "target_unit": "m3/s",
                    "missing_feature_policy": "reject",
                    "future_information_policy": "features end at issue_date",
                },
            )
            loaded = ModelBundle.load(model_dir)
            roundtrip = loaded.predict(test.iloc[[0]][feature_names].to_dict(orient="records")[0])
            before = float(predictions[0])
            after = float(roundtrip["value"])
            results[model_key] = {
                "metrics": metrics,
                "validation_metrics": validation_metrics,
                "artifact_dir": model_dir,
                "model_version": bundle.metadata.get("dataset_version"),
                "roundtrip_max_abs_error": abs(before - after),
                "y_true": y_test.tolist(),
                "y_pred": predictions.tolist(),
            }
            bundles[model_key] = model_dir

        candidate_names = [name for name in results if name != "Persistence baseline" and results[name].get("artifact_dir")]
        if not candidate_names:
            raise ValueError("At least one trainable model is required")
        best_model = min(candidate_names, key=lambda name: results[name]["metrics"]["rmse"])
        baseline_rmse = results["Persistence baseline"]["metrics"]["rmse"]
        if results[best_model]["metrics"]["rmse"] < baseline_rmse:
            champion_dir = promote_to_champion(TARGET, best_model, self.artifact_base_dir)
        else:
            best_model = "Persistence baseline"
            champion_dir = None
        report = {
            "experiment_name": "next_day_outlet_streamflow",
            "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "target": TARGET,
            "preparation": preparation,
            "split": asdict(split),
            "dataset_metadata": self.dataset_metadata,
            "random_seed": self.random_seed,
            "selected_models": list(selected_models),
            "baseline": results["Persistence baseline"],
            "models": {key: value for key, value in results.items() if key != "Persistence baseline"},
            "best_model": best_model,
            "champion_dir": champion_dir,
            "duration_seconds": round(time.time() - started, 3),
        }
        report_path = os.path.join(self.artifact_base_dir, TARGET, "experiment.json")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=True)
        return {
            "experiment_name": report["experiment_name"],
            "prepared": prepared,
            "feature_names": feature_names,
            "split": asdict(split),
            "results": results,
            "best_model": best_model,
            "champion_dir": champion_dir,
            "report_path": report_path,
            "duration_seconds": report["duration_seconds"],
        }
