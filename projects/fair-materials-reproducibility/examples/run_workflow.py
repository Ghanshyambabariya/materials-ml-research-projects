"""Run the complete workflow from the repository root."""
import json
from pathlib import Path

from fairmaterials.data import demo, validate
from fairmaterials.experiment import export_bundle, train, verify_bundle
from fairmaterials.store import Store


def main():
    root = Path("workspace")
    demo(root / "demo")
    raw = (root / "demo/materials.csv").read_bytes()
    metadata = json.loads((root / "demo/metadata.json").read_text())
    rows = validate(metadata, raw)
    store = Store(root / "store")
    dataset_id = store.ingest(root / "demo/materials.csv", root / "demo/metadata.json")
    run_id, result = train(store, dataset_id)
    destination = export_bundle(store, run_id, root / "bundles" / run_id)
    verification = verify_bundle(destination, reproduce=True)
    print(json.dumps({"measurements": len(rows), "dataset_id": dataset_id, "run_id": run_id, "metrics": result["metrics"], "baseline_metrics": result["baseline_metrics"], "bundle": str(destination), "verification": verification}, indent=2))


if __name__ == "__main__":
    main()
