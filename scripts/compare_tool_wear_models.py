"""Compare machining tool-wear models using tool-independent test groups."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline

SEED = 42


def group_split(frame, test_size, seed):
    if frame["tool"].nunique() < 3:
        raise ValueError("At least three different tools are required")
    cv = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    a, b = next(cv.split(frame, groups=frame["tool"]))
    if set(frame.iloc[a]["tool"]) & set(frame.iloc[b]["tool"]):
        raise AssertionError("A tool is present in both partitions")
    return a, b


def score(y, predicted):
    return {
        "mae": round(float(mean_absolute_error(y, predicted)), 5),
        "rmse": round(float(np.sqrt(mean_squared_error(y, predicted))), 5),
        "r2": round(float(r2_score(y, predicted)), 5),
    }


def models():
    return {
        "rf_300_baseline": RandomForestRegressor(n_estimators=300, random_state=SEED, n_jobs=-1),
        "rf_100": RandomForestRegressor(n_estimators=100, random_state=SEED, n_jobs=-1),
        "extra_trees_160": ExtraTreesRegressor(n_estimators=160, min_samples_leaf=2, random_state=SEED, n_jobs=-1),
        "hist_gradient_boosting": HistGradientBoostingRegressor(max_iter=160, learning_rate=0.06, l2_regularization=1.0, random_state=SEED),
    }


def evaluate(model, train, test, features):
    pipeline = make_pipeline(SimpleImputer(strategy="median"), model)
    start = perf_counter()
    pipeline.fit(train[features], train["Vb"])
    fit_seconds = perf_counter() - start
    start = perf_counter()
    predicted = pipeline.predict(test[features])
    predict_seconds = perf_counter() - start
    return {**score(test["Vb"], predicted),
            "fit_seconds": round(fit_seconds, 4),
            "predict_seconds": round(predict_seconds, 4)}


def run(data_path):
    frame = pd.read_csv(data_path)
    if not {"tool", "Vb"}.issubset(frame.columns):
        raise ValueError("Cleaned Vicomtech CSV must contain tool and Vb")
    frame = frame.dropna(subset=["tool", "Vb"])
    features = [col for col in frame.select_dtypes(include="number").columns
                if col not in {"tool", "Vb", "wear_stage"}]
    if not features:
        raise ValueError("No numeric input features")
    train_idx, test_idx = group_split(frame, 0.30, SEED)
    development = frame.iloc[train_idx]
    held_out = frame.iloc[test_idx]
    a, b = group_split(development, 0.25, 24)
    fit, validation = development.iloc[a], development.iloc[b]

    # The test tools do not participate in model selection.
    validation_results = {name: evaluate(model, fit, validation, features)
                          for name, model in models().items()}
    reference = validation_results["rf_300_baseline"]
    eligible = [name for name, metrics in validation_results.items()
                if metrics["rmse"] <= 1.05 * reference["rmse"]]
    selected = min(eligible, key=lambda name: (
        validation_results[name]["fit_seconds"],
        validation_results[name]["rmse"],
        name,
    ))
    final_models = models()
    baseline_test = evaluate(final_models["rf_300_baseline"], development, held_out, features)
    selected_test = (baseline_test if selected == "rf_300_baseline"
                     else evaluate(final_models[selected], development, held_out, features))
    speedup = baseline_test["fit_seconds"] / max(selected_test["fit_seconds"], 1e-9)
    return {
        "dataset": "Vicomtech machine tool wear (measured, public)",
        "rows": int(len(frame)),
        "features": len(features),
        "tools": int(frame["tool"].nunique()),
        "development_groups": sorted(development["tool"].astype(str).unique().tolist()),
        "validation_groups": sorted(validation["tool"].astype(str).unique().tolist()),
        "test_groups": sorted(held_out["tool"].astype(str).unique().tolist()),
        "validation_models": validation_results,
        "selected_using_validation_only": selected,
        "test_baseline": baseline_test,
        "test_selected": selected_test,
        "fit_speedup": round(speedup, 3),
        "accuracy_goal_met": selected_test["rmse"] <= baseline_test["rmse"] * 1.05,
        "training_speed_goal_met": selected_test["fit_seconds"] < baseline_test["fit_seconds"],
        "note": "Training times depend on hardware. No improvement to machine productivity was measured.",
    }


def write_report(result, output):
    output.mkdir(parents=True, exist_ok=True)
    (output / "model_comparison.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    base, selected = result["test_baseline"], result["test_selected"]
    lines = [
        "# Tool-wear model efficiency",
        "",
        "Public Vicomtech data. Complete tool groups are held out; model selection uses development tools only.",
        "",
        f"Samples: {result['rows']}. Features: {result['features']}. Tools: {result['tools']}.",
        "",
        "| Model | Test RMSE | Test MAE | Test R² | Fit seconds |",
        "|---|---:|---:|---:|---:|",
        f"| Random Forest, 300 trees | {base['rmse']:.3f} | {base['mae']:.3f} | {base['r2']:.3f} | {base['fit_seconds']:.2f} |",
        f"| {result['selected_using_validation_only']} | {selected['rmse']:.3f} | {selected['mae']:.3f} | {selected['r2']:.3f} | {selected['fit_seconds']:.2f} |",
        "",
        f"Training speedup on the same runner: {result['fit_speedup']:.2f}x.",
        f"RMSE within 5% of baseline: {result['accuracy_goal_met']}. Faster fitting: {result['training_speed_goal_met']}.",
        "",
        "Measured performance is for prediction, not a proven reduction in machining time or scrap.",
        "Dataset: https://github.com/Vicomtech/dataset-machine-tool-wear",
        "",
    ]
    (output / "model_comparison.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data/processed/vicomtech_tool_wear_clean.csv"))
    parser.add_argument("--output", type=Path, default=Path("projects/tool-wear-prediction/benchmarks"))
    args = parser.parse_args()
    if not args.data.is_file():
        parser.error("Cleaned data missing. Run scripts/run_external_tool_wear.py first.")
    results = run(args.data)
    write_report(results, args.output)
    print(json.dumps({"selected": results["selected_using_validation_only"],
                      "baseline": results["test_baseline"], "selected_test": results["test_selected"],
                      "speedup": results["fit_speedup"],
                      "goals_met": [results["accuracy_goal_met"], results["training_speed_goal_met"]]}, indent=2))
