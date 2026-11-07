"""Command-line entry point."""
import argparse
import json
from pathlib import Path

from jsonschema import ValidationError

from .data import demo, validate
from .experiment import export_bundle, train, verify_bundle
from .store import Store


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
        else:
            store = Store(args.root)
            if args.command == "ingest":
                output = {"dataset_id": store.ingest(args.csv, args.metadata)}
            elif args.command == "search":
                output = store.search(args.query)
            elif args.command == "train":
                run_id, result = train(store, args.dataset_id, args.seed, args.test_fraction, args.alpha)
                output = {"run_id": run_id, "metrics": result["metrics"], "baseline_metrics": result["baseline_metrics"]}
            else:
                output = {"destination": str(export_bundle(store, args.run_id, args.destination))}
        print(json.dumps(output, indent=2))
    except (ValueError, OSError, ValidationError, KeyError) as error:
        parser.exit(2, f"error: {error}\n")
