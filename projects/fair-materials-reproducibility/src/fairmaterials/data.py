"""Validate a fixed, explicitly unit-bearing materials table."""
import csv
import hashlib
import io
import json
import math
from importlib.resources import files
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

COLUMNS = ["measurement_id", "specimen_id", "temperature_k", "density_g_cm3", "porosity_fraction", "strength_mpa"]
FEATURES = COLUMNS[2:5]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def validate(metadata: dict, raw: bytes) -> list[dict]:
    schema = json.loads(files("fairmaterials").joinpath("metadata.schema.json").read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(metadata)
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
    if reader.fieldnames != COLUMNS:
        raise ValueError(f"CSV columns must be exactly {COLUMNS}")
    rows, ids = [], set()
    for row in reader:
        if None in row or any(v is None or not v.strip() for v in row.values()):
            raise ValueError("Missing or extra CSV values")
        if row["measurement_id"] in ids:
            raise ValueError("Duplicate measurement_id")
        ids.add(row["measurement_id"])
        for key in COLUMNS[2:]:
            row[key] = float(row[key])
            if not math.isfinite(row[key]):
                raise ValueError(f"Non-finite {key}")
        if not (row["temperature_k"] > 0 and row["density_g_cm3"] > 0 and row["strength_mpa"] >= 0 and 0 <= row["porosity_fraction"] < 1):
            raise ValueError("Values outside supported physical ranges")
        rows.append(row)
    if not rows:
        raise ValueError("Dataset is empty")
    return rows


def demo(destination: Path) -> None:
    """Generate demonstration values; the equation is not a physical model."""
    import random
    destination.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)
    with (destination / "materials.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(COLUMNS)
        for specimen in range(60):
            density, porosity = rng.uniform(2, 8), rng.uniform(0.01, 0.3)
            offset = rng.gauss(0, 8)
            for repeat in range(3):
                temperature = rng.uniform(280, 800)
                strength = 130 + 35*density - 160*porosity - 0.08*temperature + offset + rng.gauss(0, 3)
                writer.writerow([f"m{specimen:03d}-{repeat}", f"s{specimen:03d}", f"{temperature:.5f}", f"{density:.5f}", f"{porosity:.5f}", f"{strength:.5f}"])
    metadata = {
        "identifier": "87370b13-1ab1-4cbb-97ef-0faf74655b23", "title": "Synthetic materials strength demonstration",
        "description": "Synthetic repeated specimen measurements for workflow testing; not laboratory observations.",
        "creator": "Materials workflow demonstration", "license": "CC0-1.0", "created": "2026-11-07", "version": "1.0.0",
        "keywords": ["materials", "synthetic", "strength"],
        "provenance": {"kind": "synthetic", "method": "Python random.Random(42); 60 specimens x 3 repeats; strength = 130 + 35*density - 160*porosity - 0.08*temperature + specimen offset N(0,8) + noise N(0,3). Not a physical law."},
        "units": {"temperature_k": "K", "density_g_cm3": "g/cm^3", "porosity_fraction": "1", "strength_mpa": "MPa"}
    }
    (destination / "metadata.json").write_bytes(canonical(metadata))
