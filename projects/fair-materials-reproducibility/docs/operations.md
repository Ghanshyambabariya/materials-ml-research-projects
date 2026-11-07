# Storage operations

## Catalog and objects

The application runs locally through a command-line interface. A storage root contains `catalog.sqlite`, `objects/`, and `runs/`. SQLite holds dataset and artifact relationships and the authoritative run manifests. Object paths are content-addressed. Run JSON files are convenience copies of SQL records.

Dataset identities are immutable. Repeated ingestion of identical data and metadata is idempotent. A changed data/metadata snapshot has a distinct UUID. Object integrity is checked during loading and artifact retrieval.

Atomic file writes and SQL transactions have separate durability boundaries. An interrupted operation can leave unreferenced files or a missing run convenience copy. Audit lists orphan objects without deleting them. The backup process reconstructs run copies from SQL.

## Audit

The `audit` command checks SQLite integrity, foreign keys, data and metadata hashes, artifact hashes and sizes, run-to-dataset provenance, and existing run copies. Its JSON report contains record counts, errors, and unreferenced objects. Detected errors produce exit status 1.

## Backup

The `backup` command creates a consistent SQLite snapshot through the online backup API, copies its referenced objects, reconstructs run copies, audits the result, and writes a checksum manifest. A successful snapshot is published by staging-directory rename. Existing destinations and destinations inside the live storage root are rejected.

Concurrent append-only registration is compatible with the catalog snapshot. Mutation or deletion of referenced objects during copying is outside the supported operating model. Ordinary errors remove staging files; forced process termination can leave a staging directory.

## Restore

The `restore` command verifies backup checksums, rejects escaping paths, copies verified files into staging, audits the catalog, and publishes a successful restoration to a new directory. Existing destinations are rejected. The implemented restore model assumes trusted backup sources.

## Operating boundaries

The application has no network API, identity service, multi-user authorization layer, automated retention, encryption, or remote replication. SQLite storage is single-host. Checksum verification detects corruption without providing cryptographic authenticity. Backups retain the sensitivity of source data.

Portable evaluation bundles contain tabular inputs and evaluation evidence. Opaque attached artifacts are accessible through verified retrieval and complete storage snapshots.
