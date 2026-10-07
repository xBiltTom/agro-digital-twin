"""Small, frozen TRAIN/VALIDATION experiment for observed monthly outlet residuals."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge

from src.core.features.preprocessor import MultiScaleDataPreprocessor
from src.core.features.schema import FeatureDefinition, ModelFeatureSchema
from src.core.inference.bundle import ModelBundle
from src.core.metrics import calculate_rmse
from src.core.training.residual import corrected_flow, validation_winner


class MonthlyEstimator:
    """Use the existing bundle format with a plain sklearn estimator."""
    model_type = "traditional"

    def __init__(self, family, parameters, seed):
        self.name = f"Monthly residual {family}"
        self.estimator = Ridge(**parameters) if family == "ridge" else RandomForestRegressor(
            **parameters, random_state=seed)

    def fit(self, x, y):
        self.estimator.fit(x, y)

    def predict(self, x):
        return self.estimator.predict(x)

    def save(self, artifact_dir):
        path = Path(artifact_dir) / "model.joblib"
        joblib.dump({"estimator": self.estimator}, path)
        return str(path)


def prepare_arm(frame, protocol, arm):
    """Keep targets, physical baseline and calendar keys outside scaled arrays."""
    physical_arm = {"C": "A", "D": "B"}[arm]
    work = frame.loc[frame.arm == physical_arm].sort_values("month").copy()
    dates = pd.to_datetime(work.month + "-01", errors="raise")
    expected = pd.period_range("2013-01", "2020-12", freq="M").astype(str).tolist()
    if work.month.tolist() != expected or set(work.station_id) != {protocol["station_id"]}:
        raise ValueError("Expected one unique paired station series for 2013–2020")
    partition = np.where(work.month <= protocol["partitions"]["TRAIN"][1], "TRAIN", "VALIDATION")
    if not np.array_equal(work.partition, partition):
        raise ValueError("Partition labels disagree with the frozen dates")
    target = work.observed_streamflow_m3s.to_numpy(dtype=float)
    baseline = work.physical_streamflow_m3s.to_numpy(dtype=float)
    if not np.isfinite(target).all() or not np.isfinite(baseline).all() or min(target.min(), baseline.min()) < 0:
        raise ValueError("Observed and physical Q must be finite and nonnegative")
    if not np.allclose(target - baseline, work.residual_streamflow_m3s, rtol=0, atol=1e-12):
        raise ValueError("Residual target differs from observed minus physical Q")
    work[protocol["baseline_feature"]] = baseline
    work["month_sin"] = np.sin(2 * np.pi * (dates.dt.month - 1) / 12)
    work["month_cos"] = np.cos(2 * np.pi * (dates.dt.month - 1) / 12)
    features = list(protocol["common_features"])
    if arm == "D":
        work["fspm_active_fraction"] = work.fspm_active_days / work.expected_days
        work["fspm_stress_available_fraction"] = work.fspm_water_stress_available_days / work.expected_days
        if ((work.fspm_stress_available_fraction < 0) | (work.fspm_stress_available_fraction > work.fspm_active_fraction) | (work.fspm_active_fraction > 1)).any():
            raise ValueError("Invalid FSPM activity/availability support")
        if not np.array_equal(work.fspm_water_stress.notna(), work.fspm_water_stress_available_days > 0):
            raise ValueError("Stress nullability disagrees with available days")
        work["fspm_water_stress"] = work.fspm_water_stress.fillna(0.0)
        features += protocol["fspm_features"]
    if set(features) & set(protocol["feature_policy"]["excluded"]):
        raise ValueError("Target or observation metadata entered the feature set")
    if not np.isfinite(work[features].to_numpy(dtype=float)).all():
        raise ValueError("Unknown/nonfinite model features require a new missing-data protocol")
    return work, features


def simple_references(frame):
    """Fit calendar climatology and two constrained affine corrections on TRAIN."""
    a = frame.loc[frame.arm == "A"].sort_values("month")
    train = a[a.partition == "TRAIN"]
    climatology = train.groupby(train.month.str[-2:]).observed_streamflow_m3s.mean().to_dict()
    affine = {}
    for arm in ("A", "B"):
        rows = frame[(frame.arm == arm) & (frame.partition == "TRAIN")]
        x, y = rows.physical_streamflow_m3s.to_numpy(), rows.observed_streamflow_m3s.to_numpy()
        variance = np.mean((x - x.mean()) ** 2)
        slope = max(0.0, float(np.mean((x - x.mean()) * (y - y.mean())) / variance)) if variance > 0 else 0.0
        affine[arm] = {"slope": slope, "intercept": float(y.mean() - slope * x.mean())}
    return {"fit_partition": "TRAIN", "fit_months": 60, "climatology": climatology, "affine": affine}


def run_experiment(frame, protocol, units, output, dataset_metadata):
    """Select on corrected validation Q; retain TRAIN-only winner weights."""
    if set(frame.partition) != {"TRAIN", "VALIDATION"} or len(frame) != 192:
        raise ValueError("Delivery 3 accepts only the 192 development A/B rows")
    if frame.duplicated(["station_id", "month", "arm"]).any():
        raise ValueError("Duplicate dated station/arm keys")
    a, b = [frame[frame.arm == arm].sort_values("month") for arm in ("A", "B")]
    if not np.array_equal(a.month, b.month) or not np.array_equal(a.observed_streamflow_m3s, b.observed_streamflow_m3s) or not np.array_equal(a.paired_days, b.paired_days):
        raise ValueError("A/B observed monthly support is not identical")
    if len(protocol["candidates"]) != protocol["max_candidates_per_arm"]:
        raise ValueError("Candidate budget differs from frozen protocol")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    candidates, candidate_predictions, corrected = [], [], []
    selection = {}
    for arm in ("C", "D"):
        work, features = prepare_arm(frame, protocol, arm)
        schema = ModelFeatureSchema([FeatureDefinition(name, "float",
            units.get(name, "m3/s" if name == protocol["baseline_feature"] else "fraction"),
            "Field" if name.startswith("fspm_") else "Climate/Watershed",
            required=True, default=None) for name in features], strict_missing=True)
        train_mask = work.partition == "TRAIN"
        validation_mask = work.partition == "VALIDATION"
        preprocessor = MultiScaleDataPreprocessor(schema=schema)
        x_train = preprocessor.fit_transform(work.loc[train_mask])
        x_all = preprocessor.transform(work)
        baseline = work.physical_streamflow_m3s.to_numpy(dtype=float)
        target = work.observed_streamflow_m3s.to_numpy(dtype=float)
        y_train = (target - baseline)[train_mask]
        fitted, scores = {}, {}
        for candidate in protocol["candidates"]:
            model = MonthlyEstimator(candidate["family"], candidate["parameters"], protocol["seed"])
            model.fit(x_train, y_train)
            prediction = corrected_flow(baseline, model.predict(x_all))
            identifier = f"{arm}-{candidate['id']}"
            score = calculate_rmse(target[validation_mask], prediction[validation_mask])
            scores[identifier] = score
            fitted[identifier] = model, prediction, candidate
            candidates.append({"arm": arm, **candidate, "id": identifier,
                "validation_rmse_m3s": score, "train_rmse_m3s": calculate_rmse(target[train_mask], prediction[train_mask]),
                "train_months": int(train_mask.sum()), "validation_months": int(validation_mask.sum())})
            for month, observed, predicted in zip(work.month[validation_mask], target[validation_mask], prediction[validation_mask]):
                candidate_predictions.append({"arm": arm, "candidate_id": identifier, "month": month,
                    "observed_streamflow_m3s": observed, "predicted_streamflow_m3s": predicted})
        winner = validation_winner(scores)
        model, prediction, candidate = fitted[winner]
        bundle_dir = output / arm
        ModelBundle.save_bundle(str(bundle_dir), model, preprocessor, schema,
            protocol["target"], "residual", {"val_rmse": scores[winner],
                "train_rmse": calculate_rmse(target[train_mask], prediction[train_mask])},
            "frozen_train_validation_only", "TRAIN 2013–2017; VALIDATION 2018–2020; TEST reserved",
            random_seed=protocol["seed"], is_champion=True, dataset_metadata=dataset_metadata,
            inference_contract={"required_features": features, "target": protocol["target"], "target_unit": "m3/s",
                "baseline_feature": protocol["baseline_feature"], "missing_feature_policy": "reject; encode stress absence with availability fraction",
                "temporal_support": "Full calendar month; retrospective", "arm": arm})
        selection[arm] = {"candidate_id": winner, "family": candidate["family"], "parameters": candidate["parameters"],
            "validation_rmse_m3s": scores[winner], "feature_names": features, "scaler_fit_samples": int(preprocessor.scaler.n_samples_seen_),
            "estimator_fit_partition": "TRAIN", "bundle": str(bundle_dir), "test_accessed": False}
        raw_residual = model.predict(x_all)
        for month, partition, observed, physical, predicted, residual in zip(work.month, work.partition, target, baseline, prediction, raw_residual):
            corrected.append({"station_id": protocol["station_id"], "month": month, "partition": partition,
                "series": arm, "observed_streamflow_m3s": observed, "physical_streamflow_m3s": physical,
                "predicted_streamflow_m3s": predicted, "predicted_residual_m3s": float(residual)})
    references = simple_references(frame)
    for _, row in frame.iterrows():
        physical = row.physical_streamflow_m3s
        for series, prediction in ((row.arm, physical), (f"AFFINE_{row.arm}", max(0, references["affine"][row.arm]["slope"] * physical + references["affine"][row.arm]["intercept"]))):
            corrected.append({"station_id": protocol["station_id"], "month": row.month, "partition": row.partition,
                "series": series, "observed_streamflow_m3s": row.observed_streamflow_m3s,
                "physical_streamflow_m3s": physical, "predicted_streamflow_m3s": prediction, "predicted_residual_m3s": None})
        if row.arm == "A":
            corrected.append({"station_id": protocol["station_id"], "month": row.month, "partition": row.partition,
                "series": "CLIMATOLOGY", "observed_streamflow_m3s": row.observed_streamflow_m3s,
                "physical_streamflow_m3s": None, "predicted_streamflow_m3s": references["climatology"][row.month[-2:]], "predicted_residual_m3s": None})
    pd.DataFrame(corrected).sort_values(["month", "series"]).to_csv(output / "development-predictions.csv", index=False)
    pd.DataFrame(candidate_predictions).to_csv(output / "candidate-validation-predictions.csv", index=False)
    report = {"schema_version": "south-fork-monthly-residual-selection/v1", "selection": selection,
        "candidates": candidates, "simple_references": references,
        "test_accessed": False, "hypothesis_status": "NOT_EVALUATED"}
    (output / "selection.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report
