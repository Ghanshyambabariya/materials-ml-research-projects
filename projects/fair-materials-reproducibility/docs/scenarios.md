# Supported scenarios and future research roadmap

## Implemented in version 0.2

| Scenario | Implemented behavior | Boundary |
| --- | --- | --- |
| Existing dataset metadata | Version-1 fields remain accepted | Dataset table remains the original strength-regression contract |
| Material-specific experiments | Optional material, batch, instrument, calibration date, processing conditions with units, and modalities | Metadata labels do not verify an experiment occurred |
| Dataset evolution | Optional parent UUID and semantic dataset version | Parent may refer to an external catalog; lineage is descriptive, not an enforced foreign key |
| Personal or institutional creator | Person/Organization choice propagated to JSON-LD | No ORCID/ROR resolution or identity verification |
| Restricted datasets | Access classification recorded | CLI has no access-control enforcement; filesystem permissions remain necessary |
| Raw files, MATLAB files, microscopy, surface metrology | Streaming opaque artifact registration and checksum-verified retrieval | No MAT/TIFF/proprietary binary parsing or acquisition driver |
| Trained weights and architecture definitions | Artifact kinds and optional run link, validated against dataset ownership | Files never execute; no framework-specific weight/architecture compatibility check |
| Calibrated force, torque, vibration, temperature CSV | Explicit units, timestamp-rate validation, RMS/peak/std/crest and Welch features | One uniformly sampled stream; no calibration, filtering, anti-aliasing, synchronization, or hardware acquisition |
| 20 kHz signals | Rate is declared and checked against timestamps | A 20 kHz CSV does not establish dynamometer integration |
| Small or malformed inputs | Validation rejects insufficient windows/groups and invalid units/numbers/configurations | Domain expert review is still required for scientific validity |
| Parameter selection | Nested GroupKFold with training-only scaling and inner-loop Ridge selection | Fixed feature set and specimen grouping; not batch/time/material-family independence |
| Uncertainty summary | Specimen-cluster bootstrap interval for fixed out-of-fold MAE | Conditional error variability; not full training uncertainty or an external validation interval |
| Portable evaluation | Nested evaluation manifests export and reproduce from bundled data | Attached artifacts are separately retrieved or included in storage backups, not copied into model-evaluation bundles |
| Storage corruption | Dataset/artifact hashes, SQL health/foreign keys, run provenance and manifest-copy audit | Checksums do not authenticate against deliberate replacement |
| Interrupted operations | Atomic file writes, SQL transactions, staging directories, no overwrite on export/retrieve/backup/restore | Unreferenced files can remain; audit reports them and never deletes them |
| Backup and recovery | SQLite backup API, referenced-object snapshot, regenerated run copies, checksums, staged restore and audit | Single-host local storage; no encryption, remote replication, retention scheduler, or service monitoring |

## Priority 1 — Integrate real, permission-cleared research data

1. Obtain representative datasets and their reuse permissions.
2. Define experiment-specific fields for Zerodur®, quartz glass, sapphire, Si3N4, and SiC with domain experts. The free-text material field already accepts these names; no such experiments are bundled.
3. Map specimen, acquisition batch, processing condition, instrument calibration, and artifact identities to source records.
4. Add format adapters only after reviewing actual MATLAB, microscope, metrology, and dynamometer exports.
5. Record uncertainty, sensor orientation, coordinate systems, calibration coefficients, and acquisition timing before interpreting signal features.

Acceptance evidence: reviewed dataset cards, raw-to-processed traceability, calibration records, documented unit conversions, and an independently reproduced real-data result.

## Priority 2 — Scientific evaluation

Add group keys for acquisition batch, laboratory, material family, and instrument; temporal holdouts for drift; nested feature selection; uncertainty propagation; and independent external datasets. Compare domain-informed baselines and report failure cases. Maintain a holdout that is not reused during exploratory tuning.

Acceptance evidence: written evaluation protocol, leakage audit, independent test data, and uncertainty assessed for the scientific question.

## Priority 3 — Managed laboratory storage

Choose institutional ownership, authentication, permissions, quotas, retention, and availability requirements. Then add an authenticated service and suitable object storage/catalog backend, backup encryption, scheduled recovery drills, monitoring, and large-file lifecycle management. The current SQLite design is for one host, not multi-host concurrent writes.

Acceptance evidence: reviewed access policy, deployment configuration, backup restoration record, and operational monitoring. No production server deployment is included in this release.

## Priority 4 — Interoperability and publication

Adopt a community materials vocabulary and typed persistent identifiers. Validate exported JSON-LD independently against the chosen RO-Crate profile. Integrate an approved DOI repository and archive source, environment, data, and artifact manifests together. Access metadata must describe actual institutional access procedures.

Acceptance evidence: conformance report, resolvable repository record, explicit license, and archived release.

## Priority 5 — Student and collaboration workflows

Add contribution exercises, reviewed example submissions, instrument/data onboarding instructions, and documented stewardship roles. Use institutional supervision records, publications, and conference records for evidence of those activities. Software features alone do not substantiate training, supervision, collaboration, or publication claims.
