import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from jsonschema import ValidationError

from fairmaterials.data import canonical, demo, digest, validate
from fairmaterials.experiment import calculate, export_bundle, train, verify_bundle
from fairmaterials.store import Store


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        demo(self.root / "input")
        self.csv = self.root / "input/materials.csv"
        self.meta = self.root / "input/metadata.json"
        self.metadata = json.loads(self.meta.read_text())
        self.store = Store(self.root / "store")

    def ingest(self):
        return self.store.ingest(self.csv, self.meta)

    def test_demo_deterministic(self):
        demo(self.root / "second")
        self.assertEqual(self.csv.read_bytes(), (self.root / "second/materials.csv").read_bytes())
        self.assertEqual(len(validate(self.metadata, self.csv.read_bytes())), 180)

    def test_metadata_rejects_bad_units_identifier_and_license(self):
        for field, value in [("identifier", "bad"), ("license", "unknown"), ("created", "2026-99-99")]:
            with self.subTest(field=field), self.assertRaises(ValidationError):
                validate({**self.metadata, field: value}, self.csv.read_bytes())
        self.metadata["units"]["temperature_k"] = "C"
        with self.assertRaises(ValidationError):
            validate(self.metadata, self.csv.read_bytes())

    def test_csv_rejects_missing_duplicate_nonfinite_and_unphysical(self):
        raw = self.csv.read_text()
        lines = raw.splitlines()
        bad = ["\n".join(lines[:2] + [lines[1]]), raw.replace("temperature_k", "temperature_c"), "\n".join([lines[0], "m0,s0,nan,4,0.1,30"]), "\n".join([lines[0], "m0,s0,300,4,1.2,30"]), lines[0], "\n".join([lines[0], "m0,s0,300,4,,30"])]
        for content in bad:
            with self.subTest(content=content[:70]), self.assertRaises(ValueError):
                validate(self.metadata, content.encode())

    def test_ingest_idempotent_and_conflict_rejected(self):
        identifier = self.ingest()
        self.assertEqual(identifier, self.ingest())
        self.assertEqual(len(self.store.search("synthetic")), 1)
        self.assertEqual(self.store.search("' OR 1=1 --"), [])
        self.metadata["title"] = "Different description"
        self.meta.write_bytes(canonical(self.metadata))
        with self.assertRaises(ValueError):
            self.ingest()

    def test_corrupted_object_rejected(self):
        identifier = self.ingest()
        record, *_ = self.store.load(identifier)
        (self.store.root / record["object_path"]).write_text("tamper")
        with self.assertRaisesRegex(ValueError, "integrity"):
            self.store.load(identifier)

    def test_metadata_corruption_rejected(self):
        identifier = self.ingest()
        with self.store.connect() as connection:
            connection.execute("UPDATE datasets SET metadata=? WHERE id=?", ('{}', identifier))
        with self.assertRaisesRegex(ValueError, "integrity"):
            self.store.load(identifier)

    def test_group_split_model_and_repeatability(self):
        identifier = self.ingest()
        _, result = train(self.store, identifier)
        _, repeat = train(self.store, identifier)
        self.assertEqual(result["metrics"], repeat["metrics"])
        self.assertTrue(set(result["split"]["train_specimens"]).isdisjoint(result["split"]["test_specimens"]))
        self.assertTrue(set(result["split"]["train_ids"]).isdisjoint(result["split"]["test_ids"]))
        self.assertLess(result["metrics"]["mae_mpa"], result["baseline_metrics"]["mae_mpa"])
        rows = validate(self.metadata, self.csv.read_bytes())
        train_ids = set(result["split"]["train_ids"])
        expected_mean = np.array([[r[k] for k in result["features"]] for r in rows if r["measurement_id"] in train_ids]).mean(axis=0)
        np.testing.assert_allclose(expected_mean, result["model"]["mean"])
        model = result["model"]
        row = next(r for r in rows if r["measurement_id"] == result["predictions"][0]["measurement_id"])
        prediction = ((np.array([row[k] for k in result["features"]])-model["mean"])/model["scale"]) @ model["coefficients"] + model["intercept"]
        self.assertAlmostEqual(prediction, result["predictions"][0]["predicted_mpa"])

    def test_export_verify_reproduce_and_tamper(self):
        run_id, _ = train(self.store, self.ingest())
        bundle = export_bundle(self.store, run_id, self.root / "bundle")
        self.assertEqual(verify_bundle(bundle, True)["reproduction"], "passed")
        with self.assertRaises(ValueError):
            export_bundle(self.store, run_id, bundle)
        (bundle / "materials.csv").write_text("corrupted")
        with self.assertRaisesRegex(ValueError, "Integrity"):
            verify_bundle(bundle)

    def test_reproduction_detects_changed_metrics_even_with_updated_checksum(self):
        run_id, _ = train(self.store, self.ingest())
        bundle = export_bundle(self.store, run_id, self.root / "bundle")
        manifest = json.loads((bundle / "manifest.json").read_text())
        manifest["metrics"]["mae_mpa"] += 10
        (bundle / "manifest.json").write_bytes(canonical(manifest))
        checksums = json.loads((bundle / "checksums.json").read_text())
        checksums["manifest.json"] = digest((bundle / "manifest.json").read_bytes())
        (bundle / "checksums.json").write_bytes(canonical(checksums))
        with self.assertRaisesRegex(ValueError, "reproduction failed"):
            verify_bundle(bundle, True)

    def test_invalid_parameters_and_small_group_count(self):
        rows = validate(self.metadata, self.csv.read_bytes())
        for params in [{"alpha": -1}, {"alpha": float("nan")}, {"test_fraction": 1}, {"seed": -1}]:
            with self.subTest(params=params), self.assertRaises(ValueError):
                calculate(rows, **params)
        with self.assertRaises(ValueError):
            calculate(rows[:9])

    def test_unknown_identifiers(self):
        with self.assertRaises(ValueError):
            self.store.load("missing")
        with self.assertRaises(ValueError):
            export_bundle(self.store, "missing", self.root / "bundle")


if __name__ == "__main__":
    unittest.main()
