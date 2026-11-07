# Technical scope

| Area | Implemented capability | Operating boundary |
| --- | --- | --- |
| Dataset metadata | Legacy metadata and optional laboratory fields | Regression table has a fixed strength-data schema |
| Laboratory context | Material, batch, instrument, calibration date, processing conditions, modalities | Metadata records supplied context; it does not verify experimental activity |
| Lineage | Parent UUID and dataset version | Parent relationships are descriptive |
| Creator metadata | Person or Organization JSON-LD entity | No external identity resolution |
| Access classification | Open, restricted, or embargoed labels | Filesystem authorization is external to the CLI |
| Heterogeneous artifacts | Raw files, weights, architectures, microscopy, metrology, signals, protocols, reports | Files remain opaque; no proprietary-format interpretation |
| Artifact association | Dataset ownership and optional matching run | No framework-specific model compatibility validation |
| Signal analysis | Calibrated, uniformly sampled physical channels | No hardware driver, filtering, calibration, anti-aliasing, or stream synchronization |
| 20 kHz data | Timestamp validation against a declared 20 kHz rate | Example signal is synthetic |
| Model selection | Nested specimen-grouped Ridge selection | Group identity is the specimen; no independent laboratory or temporal holdout |
| Error interval | Specimen-cluster bootstrap of fixed prediction errors | Conditional error interval; no model refitting during bootstrap |
| Research export | Data, metadata, evaluation manifest, JSON-LD, checksums | Attached opaque artifacts remain in storage and backups |
| Reproduction | Numerical agreement within specified tolerance | No cross-platform byte-identity guarantee |
| Integrity | Checksums, SQL relationships, run provenance | Checksums detect corruption; they do not authenticate an adversarial replacement |
| Backup and restore | Consistent catalog snapshot and verified referenced files | Single-host local storage; backups are not encrypted |
| FAIR support | Identifiers, metadata, licenses, provenance, portable representations | No external FAIR certification or persistent-identifier registration |
| JSON-LD export | Explicit RO-Crate 1.2-style structure | No independent conformance certification |

The material field accepts names including Zerodur®, quartz glass, sapphire, Si3N4, and SiC. No measurements on those materials are included.
