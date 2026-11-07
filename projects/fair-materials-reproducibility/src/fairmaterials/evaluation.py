"""Nested grouped model selection and out-of-fold evaluation."""
import importlib.metadata
import platform
from datetime import datetime, timezone

import numpy as np
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .data import FEATURES, canonical
from .experiment import revision
from .store import atomic_write


def nested(rows, seed=42, outer_folds=5, inner_folds=3, alphas=None, bootstrap_samples=200):
    alphas = [0.1, 1.0, 10.0] if alphas is None else alphas
    if not isinstance(seed, int) or not 0 <= seed <= 2**32-1:
        raise ValueError("Seed must be an unsigned 32-bit integer")
    if any(not isinstance(n, int) or n < 2 for n in [outer_folds, inner_folds]) or not isinstance(bootstrap_samples, int) or bootstrap_samples < 20:
        raise ValueError("Require at least two inner/outer folds and 20 bootstrap samples")
    if not alphas or any(not np.isfinite(a) or a <= 0 for a in alphas):
        raise ValueError("Alpha candidates must be finite and positive")
    x = np.array([[r[k] for k in FEATURES] for r in rows])
    y = np.array([r["strength_mpa"] for r in rows])
    groups = np.array([r["specimen_id"] for r in rows])
    if len(set(groups)) < outer_folds:
        raise ValueError("Insufficient specimens for outer folds")
    predictions, baseline_predictions = np.empty(len(rows)), np.empty(len(rows))
    folds = []
    def scores(indices, predicted):
        return {"mae_mpa": float(mean_absolute_error(y[indices], predicted)), "rmse_mpa": float(np.sqrt(mean_squared_error(y[indices], predicted))), "r2": float(r2_score(y[indices], predicted))}
    for number, (train, test) in enumerate(GroupKFold(outer_folds, shuffle=True, random_state=seed).split(x, y, groups)):
        if len(set(groups[train])) < inner_folds or min(len(train), len(test)) < 2:
            raise ValueError("Insufficient groups or measurements in a fold")
        inner = list(GroupKFold(inner_folds, shuffle=True, random_state=seed).split(x[train], y[train], groups[train]))
        search = GridSearchCV(make_pipeline(StandardScaler(), Ridge()), {"ridge__alpha": alphas}, cv=inner, scoring="neg_mean_absolute_error", error_score="raise", n_jobs=1)
        search.fit(x[train], y[train])
        predictions[test] = search.predict(x[test])
        baseline_predictions[test] = DummyRegressor().fit(x[train], y[train]).predict(x[test])
        folds.append({"fold": number, "alpha": float(search.best_params_["ridge__alpha"]), "train_ids": [rows[i]["measurement_id"] for i in train], "test_ids": [rows[i]["measurement_id"] for i in test], "train_specimens": sorted(set(groups[train])), "test_specimens": sorted(set(groups[test])), "inner_splits": [{"train_specimens": sorted(set(groups[train][a])), "validation_specimens": sorted(set(groups[train][b]))} for a, b in inner], "metrics": scores(test, predictions[test])})
    rng = np.random.default_rng(seed)
    unique = sorted(set(groups))
    indices = [np.flatnonzero(groups == g) for g in unique]
    absolute_errors = np.abs(y-predictions)
    bootstrap = []
    for _ in range(bootstrap_samples):
        sampled = rng.integers(0, len(unique), len(unique))
        bootstrap.append(float(absolute_errors[np.concatenate([indices[i] for i in sampled])].mean()))
    interval = np.quantile(bootstrap, [0.025, 0.975]).tolist()
    return {"protocol": "nested_group_kfold_v1", "parameters": {"seed": seed, "outer_folds": outer_folds, "inner_folds": inner_folds, "alphas": alphas, "bootstrap_samples": bootstrap_samples}, "features": FEATURES, "target": "strength_mpa", "group": "specimen_id", "folds": folds, "metrics": scores(np.arange(len(y)), predictions), "baseline_metrics": scores(np.arange(len(y)), baseline_predictions), "uncertainty": {"mae_mpa_95_percentile_interval": interval, "method": "Specimen-cluster bootstrap of fixed out-of-fold errors; conditional on these folds, not a full refit confidence interval"}, "predictions": [{"measurement_id": r["measurement_id"], "specimen_id": r["specimen_id"], "observed_mpa": float(y[i]), "predicted_mpa": float(predictions[i])} for i, r in enumerate(rows)]}


def evaluate(store, identifier, **parameters):
    record, _, _, rows = store.load(identifier)
    result = nested(rows, **parameters)
    result.update({"dataset_id": identifier, "dataset_sha256": record["sha256"], "metadata_sha256": record["metadata_sha256"], "created_at": datetime.now(timezone.utc).isoformat(), "code": revision(), "environment": {"python": platform.python_version(), "packages": {name: importlib.metadata.version(name) for name in ["fair-materials-reproducibility", "numpy", "scipy", "scikit-learn"]}}})
    run_id = store.record_run(identifier, result)
    atomic_write(store.root / "runs" / run_id / "manifest.json", canonical(result))
    return run_id, result


def compare(expected, actual, path="result"):
    """Check the full deterministic evaluation structure with numeric tolerance."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or expected.keys() != actual.keys():
            raise ValueError(f"Evaluation reproduction failed: {path}")
        for key in expected:
            compare(expected[key], actual[key], f"{path}.{key}")
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(expected) != len(actual):
            raise ValueError(f"Evaluation reproduction failed: {path}")
        for index, (a, b) in enumerate(zip(expected, actual)):
            compare(a, b, f"{path}[{index}]")
    elif isinstance(expected, (float, int)):
        if not isinstance(actual, (float, int)) or not np.isclose(expected, actual, rtol=1e-9, atol=1e-9):
            raise ValueError(f"Evaluation reproduction failed: {path}")
    elif expected != actual:
        raise ValueError(f"Evaluation reproduction failed: {path}")
