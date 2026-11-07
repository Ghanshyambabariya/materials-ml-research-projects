# Step-by-step implementation and acceptance criteria

## Step 1 — Research and define scope

Reviewed FAIR stewardship, RO-Crate packaging, grouped evaluation, leakage prevention, and transaction semantics. Decisions and primary references are recorded in `research.md`. Defined a synthetic repeated-specimen strength dataset and explicit unit contract.

## Step 2 — Implement metadata and measurement validation

Added JSON Schema 2020-12 and CSV validation. Acceptance: malformed IDs/dates, incorrect units, duplicate measurements, missing values, non-finite values, and unsupported physical ranges fail validation.

## Step 3 — Implement storage and discovery

Added a SHA-256 object directory and SQLite dataset/run tables with foreign keys and parameterized search. Acceptance: identical ingestion is idempotent, modified UUID registrations fail, corrupted object or metadata content is detected, and search inputs remain literal.

## Step 4 — Implement reproducible ML

Added specimen-grouped holdout, training-only StandardScaler, Ridge regression, and a training-mean baseline. Acceptance: no shared specimens or measurement IDs across partitions, repeated runs agree, stored coefficients reproduce predictions, and scaler statistics equal training-only statistics.

## Step 5 — Implement export and independent reproduction

Added portable CSV/JSON bundle and RO-Crate-style JSON-LD. Acceptance: bundle export refuses overwrites, checksum verification detects mutation, and independent refitting reproduces split identities, predictions, and model/baseline metrics. Changed metrics fail reproduction even when a checksum is updated.

## Step 6 — Package, document, and automate

Added the installable CLI, locked environment, complete demonstration, operational guidance, and CI for Python 3.12. Acceptance: fresh environment installation, full test suite, command-line validation, and complete workflow succeed.

## Next research and infrastructure milestones

- Replace synthetic examples with permission-cleared, domain-reviewed experimental datasets.
- Extend the implemented instrument/batch/calibration metadata with uncertainty, ORCID/ROR, and ontology terms.
- Validate the implemented nested grouped evaluation and conditional error intervals against an agreed real-data scientific protocol.
- Independently validate RO-Crate conformance and adopt a community materials metadata profile.
- Integrate an institutional repository for persistent identifiers and discoverability.
- Provision a managed storage service with authentication, backups, monitoring, and recovery drills.

These milestones are planned extensions; they are not claims of completed laboratory or server deployment work.

## Version 0.2 — Future-use extensions implemented

- Backward-compatible optional laboratory metadata and typed creators.
- Streaming opaque artifact registration, verified retrieval, and dataset/run association.
- Calibrated uniformly sampled signal features, with a synthetic 20 kHz example.
- Nested grouped hyperparameter selection and conditional cluster-bootstrap MAE intervals.
- Export/reproduction support for nested evaluation manifests.
- Catalog/object/run audits, checksum-backed snapshots, and staged backup restoration.
- Extension demonstration and 15 additional tests (26 total).

These changes implement infrastructure hooks for future research. Real laboratory integration, MATLAB adapters, independent profile validation, authenticated server deployment, and supervision/publication evidence remain outside the completed scope. Detailed acceptance boundaries are in `scenarios.md`.
