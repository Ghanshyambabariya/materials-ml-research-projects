# Storage operations and server deployment

## Current operating model

The implemented system is a local command-line application. It can run on a research server under a dedicated service account, with `--root` pointing to a private, local attached volume. It does not include a network API, authentication service, or multi-user access-control layer. No server deployment is claimed.

- Restrict the root directory to the service account and approved researchers (for example, mode 0700 for private use).
- Keep data roots outside the source checkout. Never commit real restricted datasets or environment files.
- SQLite is intended here for a single-host workflow. Do not place its database on a network filesystem or use this implementation for high-concurrency multi-host ingestion.
- Content-addressed snapshots are immutable by application convention, not operating-system write protection. Anyone with filesystem write access can alter them; integrity checks detect content changes on load.
- CSV files are never evaluated as code. Model export contains JSON parameters rather than executable serialized Python objects.

## Backup and restore

1. Pause writers to obtain a coherent catalog/object snapshot.
2. Copy the complete storage root, including `catalog.sqlite`, `objects/`, and `runs/`, to encrypted, access-controlled backup storage.
3. Record a backup manifest and retain copies according to the institution's data policy.
4. Restore into a new directory and run `search`, then load/export each dataset/run and verify exported bundles.
5. Perform a recovery drill before treating backups as an operational guarantee.

Atomic object writes and SQL transactions do not create one cross-filesystem transaction. A failed registration can leave unreferenced objects; do not remove objects automatically without auditing catalog references. Run records are authoritative in SQL; `runs/<uuid>/manifest.json` is a convenience copy. Compare the two during audits. A manifest-copy failure can occur after the SQL run commits.

## Reproducibility boundary

Use the recorded dependency versions and clean Git revision. A dirty working tree is disclosed in the run manifest but not archived automatically. For publication runs, commit code before execution and archive the source commit together with the bundle. Installed wheels outside a checkout cannot infer the original commit and report null provenance.

Checksums protect against accidental corruption; a malicious actor could replace both content and checksum manifests. For authenticated releases, use institutionally managed signatures and archive records. There is no automated retention, replication, encryption, disaster recovery, or production hardening in this reference implementation.

## Automated audit, backup, and restore (version 0.2)

`audit` checks SQLite health, foreign keys, data/metadata hashes, artifact hashes and sizes, run-to-dataset provenance, and existing manifest convenience copies. It lists unreferenced object files without deleting them. CLI audit exits 1 when errors are found. Missing run convenience copies are recoverable from the authoritative SQL record and are not treated as data loss.

`backup` uses SQLite's backup API to obtain a catalog snapshot, copies only the objects referenced by that snapshot, reconstructs run copies, audits the result, and publishes it by renaming a staging directory. `restore` verifies the listed checksums, rejects escaping paths, copies into a new staging directory, audits the restored catalog, and publishes only a successful result. Both refuse existing destinations. A backup destination must be outside the live store.

Concurrent append-only registrations can proceed while taking a SQLite snapshot. Do not mutate or delete object files during backup. Database and object corruption cause backup/restore to fail; staging is cleaned on ordinary errors. Process termination can leave a staging directory for manual review. Filesystem power-loss guarantees and hostile backup-file execution are outside this implementation's trust model: only restore backups from trusted sources. Backups are not encrypted and preserve the sensitivity of their source data.

Dataset bundles contain the tabular input and evaluation evidence. Generic attached artifacts are handled through verified retrieval and full storage backup/restore; they are not silently added to evaluation bundles.
