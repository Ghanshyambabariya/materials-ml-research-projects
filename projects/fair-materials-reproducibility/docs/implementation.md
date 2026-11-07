# Implementation

| Component | Completed work | Validation |
| --- | --- | --- |
| Metadata | JSON Schema 2020-12, UUID/date validation, unit contract, optional laboratory context | Invalid identifiers, units, dates, and non-finite conditions rejected |
| Measurement data | Fixed-schema CSV ingestion and physical-range checks | Missing, duplicate, malformed, non-finite, and out-of-range values rejected |
| Catalog | Dataset, run, and artifact records in SQLite; parameterized metadata search | Idempotent ingestion, immutable dataset identities, literal search inputs |
| Object storage | SHA-256 snapshots, streaming artifact registration, verified retrieval | Corruption detection, file roundtrip, overwrite protection |
| Holdout regression | Specimen-grouped split, training-only scaling, Ridge model and mean baseline | Disjoint partitions, repeatable metrics, portable coefficient prediction |
| Nested evaluation | Grouped inner/outer folds, Ridge parameter selection, pooled out-of-fold predictions | No specimen overlap, complete outer coverage, independent numerical reproduction |
| Error summary | Specimen-cluster bootstrap of fixed out-of-fold errors | Deterministic resampling and interval generation |
| Signal analysis | Uniform timestamps, physical-unit checks, windowed time/frequency features | Known synthetic frequency, amplitude, and PSD variance recovered |
| Research bundles | CSV, JSON metadata, run manifest, RO-Crate-style JSON-LD, checksums | Input integrity, split/metric/prediction reproduction |
| Audit | SQL health, foreign keys, object checksums, run provenance, manifest copies | Corruption and mismatched run copies reported |
| Recovery | SQLite backup snapshot, referenced-object copy, staged verified restore | Complete data/run/artifact recovery and invalid-path rejection |
| Automation | Locked environment, installable package, command-line workflow, CI | 26 automated tests and two executable demonstrations |

Dataset and signal examples are synthetic. No laboratory acquisition, student supervision, publication activity, or managed server deployment is represented by these software tests.
