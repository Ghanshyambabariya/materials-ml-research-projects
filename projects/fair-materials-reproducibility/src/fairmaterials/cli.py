"""Command-line entry point."""
import argparse
import json
import sqlite3
from pathlib import Path

from jsonschema import ValidationError

from .data import demo, validate
from .experiment import export_bundle, train, verify_bundle
from .store import Store
from .artifacts import KINDS, list_artifacts, register, retrieve
from .evaluation import evaluate
from .operations import audit, backup, restore
from .signals import extract


def main(argv=None):
    parser = argparse.ArgumentParser(description="Materials dataset catalog and reproducible ML workflow")
    parser.add_argument("--root", default="workspace", help="Storage root (default: workspace)")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("demo", help="Generate deterministic synthetic data")
    p.add_argument("destination", type=Path)
    for command in ["validate", "ingest"]:
        p = sub.add_parser(command)
        p.add_argument("csv", type=Path)
        p.add_argument("metadata", type=Path)
    p = sub.add_parser("search")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--material")
    p.add_argument("--data-kind", choices=["synthetic", "experimental"])
    p = sub.add_parser("train")
    p.add_argument("dataset_id")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--test-fraction", type=float, default=0.2)
    p.add_argument("--alpha", type=float, default=1.0)
    p = sub.add_parser("export")
    p.add_argument("run_id")
    p.add_argument("destination", type=Path)
    p = sub.add_parser("verify")
    p.add_argument("destination", type=Path)
    p.add_argument("--reproduce", action="store_true")
    p = sub.add_parser("evaluate", help="Nested specimen-grouped model selection")
    p.add_argument("dataset_id")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--outer-folds", type=int, default=5)
    p.add_argument("--inner-folds", type=int, default=3)
    p.add_argument("--alphas", type=float, nargs="+", default=[0.1, 1.0, 10.0])
    p.add_argument("--bootstrap-samples", type=int, default=200)
    p = sub.add_parser("artifact-add", help="Register an opaque file without executing it")
    p.add_argument("dataset_id")
    p.add_argument("source", type=Path)
    p.add_argument("--kind", choices=sorted(KINDS), required=True)
    p.add_argument("--description", required=True)
    p.add_argument("--media-type", default="application/octet-stream")
    p.add_argument("--run-id")
    p = sub.add_parser("artifact-list")
    p.add_argument("dataset_id")
    p = sub.add_parser("artifact-get")
    p.add_argument("artifact_id")
    p.add_argument("destination", type=Path)
    p = sub.add_parser("signal-features", help="Analyze calibrated uniformly sampled CSV channels")
    p.add_argument("csv", type=Path)
    p.add_argument("units", type=Path, help="JSON map of channel names to physical units")
    p.add_argument("--sampling-rate-hz", type=float, required=True)
    p.add_argument("--window-samples", type=int, default=2048)
    sub.add_parser("audit", help="Check catalog, data, artifacts, and run provenance")
    p = sub.add_parser("backup")
    p.add_argument("destination", type=Path)
    p = sub.add_parser("restore")
    p.add_argument("source", type=Path)
    p.add_argument("destination", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            demo(args.destination)
            output = {"destination": str(args.destination), "kind": "synthetic"}
        elif args.command == "validate":
            rows = validate(json.loads(args.metadata.read_text()), args.csv.read_bytes())
            output = {"valid": True, "measurements": len(rows), "specimens": len({row['specimen_id'] for row in rows})}
        elif args.command == "verify":
            output = verify_bundle(args.destination, args.reproduce)
        elif args.command == "signal-features":
            output = extract(args.csv, args.sampling_rate_hz, json.loads(args.units.read_text()), args.window_samples)
        elif args.command == "restore":
            output = restore(args.source, args.destination)
        else:
            store = Store(args.root)
            if args.command == "ingest":
                output = {"dataset_id": store.ingest(args.csv, args.metadata)}
            elif args.command == "search":
                output = store.search(args.query, args.material, args.data_kind)
            elif args.command == "train":
                run_id, result = train(store, args.dataset_id, args.seed, args.test_fraction, args.alpha)
                output = {"run_id": run_id, "metrics": result["metrics"], "baseline_metrics": result["baseline_metrics"]}
            elif args.command == "evaluate":
                run_id, result = evaluate(store, args.dataset_id, seed=args.seed, outer_folds=args.outer_folds, inner_folds=args.inner_folds, alphas=args.alphas, bootstrap_samples=args.bootstrap_samples)
                output = {"run_id": run_id, "metrics": result["metrics"], "uncertainty": result["uncertainty"]}
            elif args.command == "artifact-add":
                output = {"artifact_id": register(store, args.dataset_id, args.source, args.kind, args.description, args.media_type, args.run_id)}
            elif args.command == "artifact-list":
                output = list_artifacts(store, args.dataset_id)
            elif args.command == "artifact-get":
                output = retrieve(store, args.artifact_id, args.destination)
            elif args.command == "audit":
                output = audit(store)
            elif args.command == "backup":
                output = backup(store, args.destination)
            else:
                output = {"destination": str(export_bundle(store, args.run_id, args.destination))}
        print(json.dumps(output, indent=2, allow_nan=False))
        if args.command == "audit" and not output["ok"]:
            parser.exit(1)
    except (ValueError, OSError, ValidationError, KeyError, sqlite3.Error) as error:
        parser.exit(2, f"error: {error}\n")
