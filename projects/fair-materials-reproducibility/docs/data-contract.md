# Data contract

Each dataset consists of one UTF-8 CSV and one JSON metadata document. Schema source: `src/fairmaterials/metadata.schema.json`.

## Measurement table

Columns must occur in exactly this order. Missing values, duplicate measurement IDs, non-finite numbers, and extra columns are rejected.

| Column | Type | Units / condition |
| --- | --- | --- |
| measurement_id | string | Unique nonempty measurement identity |
| specimen_id | string | Nonempty physical-specimen identity; repeated measurements share it |
| temperature_k | number | Kelvin; > 0 |
| density_g_cm3 | number | g/cm³; > 0 |
| porosity_fraction | number | Dimensionless; 0 ≤ x < 1 |
| strength_mpa | number | MPa; ≥ 0; regression target |

Training requires at least five distinct specimens and at least two measurements in each partition. It does not infer units or convert values. Convert source values before ingestion, documenting conversion and measurement methods in provenance. Physical-range checks are basic quality gates, not a scientific validity assessment.

## Metadata fields

Required: `identifier` (UUID), `title`, `description`, `creator`, `license`, `created` (ISO date), `version` (three numeric components), `keywords`, `provenance` (`kind` and `method`), and `units`. The supported licenses are CC0-1.0 and CC-BY-4.0. Other licenses require an explicit reviewed schema extension. Provenance kind is `synthetic` or `experimental`. The creator string is currently exported as an Organization; extend the contract with typed Person/Organization entities before importing personal creator records.

An identifier represents one immutable data-and-metadata snapshot. When either changes, mint a new UUID and update the human-readable version. Dataset identity, SHA-256 content identity, and a future resolvable repository DOI serve different purposes.

## Experiment manifest

Contains dataset UUID and data/metadata hashes, UTC creation time, Git commit and dirty state (null outside a checkout), Python/platform/package versions, feature order, model coefficients and scaling, parameters, partition identities, observed/predicted test values, and model/baseline MAE, RMSE, and R². No credentials or environment variables are collected.

`requirements.lock` pins the installation environment. Run manifests record the effective core scientific packages at execution. Reproduce with the same environment where practical; verification compares numerical outputs with tolerance and fails on differences.
