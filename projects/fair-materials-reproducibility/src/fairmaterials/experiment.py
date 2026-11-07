"""Grouped holdout regression and portable research bundles."""
import importlib.metadata
import json
import platform
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .data import FEATURES, canonical, digest, validate
from .store import atomic_write


def revision():
    source = Path(__file__).resolve().parent
    def git(*args):
        return subprocess.check_output(["git", "-C", str(source), *args], stderr=subprocess.DEVNULL, text=True).strip()
    try:
        return {"commit": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain"))}
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {"commit": None, "dirty": None}


def calculate(rows, seed=42, test_fraction=0.2, alpha=1.0):
    if not isinstance(seed, int) or seed < 0 or seed > 2**32 - 1:
        raise ValueError("Seed must be an unsigned 32-bit integer")
    if not 0 < test_fraction < 1 or not np.isfinite(alpha) or alpha <= 0:
        raise ValueError("Require 0 < test_fraction < 1 and finite alpha > 0")
    groups = np.array([row["specimen_id"] for row in rows])
    if len(set(groups)) < 5:
        raise ValueError("At least five distinct specimens are required")
    x = np.array([[row[key] for key in FEATURES] for row in rows])
    y = np.array([row["strength_mpa"] for row in rows])
    train, test = next(GroupShuffleSplit(n_splits=1, test_size=test_fraction, random_state=seed).split(x, y, groups))
    if len(test) < 2 or len(train) < 2:
        raise ValueError("Train and test partitions each need at least two measurements")
    model = make_pipeline(StandardScaler(), Ridge(alpha=alpha))
    model.fit(x[train], y[train])
    predictions = model.predict(x[test])
    baseline = DummyRegressor(strategy="mean").fit(x[train], y[train]).predict(x[test])
    def scores(pred):
        return {"mae_mpa": float(mean_absolute_error(y[test], pred)), "rmse_mpa": float(np.sqrt(mean_squared_error(y[test], pred))), "r2": float(r2_score(y[test], pred))}
    scaler, ridge = model.steps[0][1], model.steps[1][1]
    return {
        "parameters": {"seed": seed, "test_fraction": test_fraction, "alpha": alpha},
        "features": FEATURES, "target": "strength_mpa", "group": "specimen_id",
        "split": {"train_ids": [rows[i]["measurement_id"] for i in train], "test_ids": [rows[i]["measurement_id"] for i in test], "train_specimens": sorted(set(groups[train])), "test_specimens": sorted(set(groups[test]))},
        "metrics": scores(predictions), "baseline_metrics": scores(baseline),
        "model": {"kind": "StandardScaler+Ridge", "mean": scaler.mean_.tolist(), "scale": scaler.scale_.tolist(), "coefficients": ridge.coef_.tolist(), "intercept": float(ridge.intercept_)},
        "predictions": [{"measurement_id": rows[i]["measurement_id"], "observed_mpa": float(y[i]), "predicted_mpa": float(predictions[j])} for j, i in enumerate(test)]
    }


def train(store, identifier, seed=42, test_fraction=0.2, alpha=1.0):
    record, metadata, raw, rows = store.load(identifier)
    result = calculate(rows, seed, test_fraction, alpha)
    result.update({"dataset_id": identifier, "dataset_sha256": digest(raw), "metadata_sha256": record["metadata_sha256"], "created_at": datetime.now(timezone.utc).isoformat(), "code": revision(), "environment": {"python": platform.python_version(), "platform": platform.platform(), "packages": {name: importlib.metadata.version(name) for name in ["fair-materials-reproducibility", "numpy", "scipy", "scikit-learn", "jsonschema", "joblib", "threadpoolctl"]}}})
    run_id = store.record_run(identifier, result)
    atomic_write(store.root / "runs" / run_id / "manifest.json", canonical(result))
    return run_id, result


def export_bundle(store, run_id, destination):
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError("Export destination must not already exist")
    with store.connect() as connection:
        row = connection.execute("SELECT dataset_id,manifest FROM runs WHERE id=?", (run_id,)).fetchone()
    if row is None:
        raise ValueError("Unknown run identifier")
    record, metadata, raw, _ = store.load(row["dataset_id"])
    manifest = json.loads(row["manifest"])
    if manifest["dataset_sha256"] != digest(raw) or manifest["metadata_sha256"] != record["metadata_sha256"]:
        raise ValueError("Run and dataset provenance differ")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".bundle-", dir=destination.parent))
    try:
        atomic_write(staging / "materials.csv", raw)
        atomic_write(staging / "metadata.json", canonical(metadata))
        atomic_write(staging / "manifest.json", canonical(manifest))
        license_url = {"CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/", "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/"}[metadata["license"]]
        graph = [
            {"@id": "ro-crate-metadata.json", "@type": "CreativeWork", "conformsTo": {"@id": "https://w3id.org/ro/crate/1.2"}, "about": {"@id": "./"}},
            {"@id": "./", "@type": "Dataset", "name": metadata["title"], "description": metadata["description"], "datePublished": metadata["created"], "license": {"@id": license_url}, "creator": {"@id": "#creator"}, "identifier": f"urn:uuid:{metadata['identifier']}", "hasPart": [{"@id": name} for name in ["materials.csv", "metadata.json", "manifest.json"]]},
            {"@id": "#creator", "@type": metadata.get("creator_type", "Organization"), "name": metadata["creator"]},
            {"@id": license_url, "@type": "CreativeWork", "name": metadata["license"]}
        ]
        for name in ["materials.csv", "metadata.json", "manifest.json"]:
            graph.append({"@id": name, "@type": "File", "name": name, "encodingFormat": "text/csv" if name.endswith("csv") else "application/json"})
        atomic_write(staging / "ro-crate-metadata.json", canonical({"@context": "https://w3id.org/ro/crate/1.2/context", "@graph": graph}))
        checksums = {file.name: digest(file.read_bytes()) for file in sorted(staging.iterdir())}
        atomic_write(staging / "checksums.json", canonical(checksums))
        staging.rename(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return destination


def verify_bundle(destination, reproduce=False):
    destination = Path(destination)
    checksums = json.loads((destination / "checksums.json").read_text())
    expected = {"materials.csv", "metadata.json", "manifest.json", "ro-crate-metadata.json"}
    if set(checksums) != expected:
        raise ValueError("Unexpected bundle checksum entries")
    for name, sha in checksums.items():
        if digest((destination / name).read_bytes()) != sha:
            raise ValueError(f"Integrity check failed: {name}")
    raw = (destination / "materials.csv").read_bytes()
    meta_raw = (destination / "metadata.json").read_bytes()
    metadata = json.loads(meta_raw)
    rows = validate(metadata, raw)
    manifest = json.loads((destination / "manifest.json").read_text())
    if manifest["dataset_id"] != metadata["identifier"] or manifest["dataset_sha256"] != digest(raw) or manifest["metadata_sha256"] != digest(meta_raw):
        raise ValueError("Bundle provenance mismatch")
    if reproduce and manifest.get("protocol") == "nested_group_kfold_v1":
        from .evaluation import compare, nested
        result = nested(rows, **manifest["parameters"])
        compare(result, {key: manifest[key] for key in result})
    elif reproduce:
        result = calculate(rows, **manifest["parameters"])
        if result["split"] != manifest["split"] or result["features"] != manifest["features"]:
            raise ValueError("Split or feature reproduction failed")
        for key in ["mean", "scale", "coefficients", "intercept"]:
            if not np.allclose(result["model"][key], manifest["model"][key], rtol=1e-9, atol=1e-9):
                raise ValueError(f"Model reproduction failed: {key}")
        if result["target"] != manifest["target"] or result["group"] != manifest["group"]:
            raise ValueError("Target or grouping reproduction failed")
        for category in ["metrics", "baseline_metrics"]:
            for key, value in result[category].items():
                if not np.isclose(value, manifest[category][key], rtol=1e-9, atol=1e-9):
                    raise ValueError(f"Metric reproduction failed: {category}.{key}")
        if [r["measurement_id"] for r in result["predictions"]] != [r["measurement_id"] for r in manifest["predictions"]] or not np.allclose([r["predicted_mpa"] for r in result["predictions"]], [r["predicted_mpa"] for r in manifest["predictions"]], rtol=1e-9, atol=1e-9):
            raise ValueError("Prediction reproduction failed")
    return {"integrity": "passed", "reproduction": "passed" if reproduce else "not_requested", "dataset_id": metadata["identifier"]}
