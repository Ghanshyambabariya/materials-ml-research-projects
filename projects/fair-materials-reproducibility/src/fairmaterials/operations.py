"""Catalog audits and consistent SQLite-backed storage snapshots."""
import json
import shutil
import sqlite3
import tempfile
import uuid

from jsonschema import ValidationError
from pathlib import Path

from .artifacts import file_digest, object_path
from .data import canonical, digest
from .store import Store, atomic_write


def audit(store):
    errors = []
    with store.connect() as connection:
        health = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if health != "ok":
            errors.append(f"SQLite integrity: {health}")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            errors.append("Foreign key violations")
        datasets = [dict(r) for r in connection.execute("SELECT * FROM datasets")]
        runs = [dict(r) for r in connection.execute("SELECT * FROM runs")]
        artifacts = [dict(r) for r in connection.execute("SELECT * FROM artifacts")]
    referenced = set()
    for dataset in datasets:
        try:
            referenced.add(str(object_path(store, dataset["object_path"])))
            store.load(dataset["id"])
        except (OSError, ValueError, KeyError, ValidationError) as error:
            errors.append(f"Dataset {dataset['id']}: {error}")
    for artifact in artifacts:
        try:
            path = object_path(store, artifact["object_path"])
            referenced.add(str(path))
            if file_digest(path) != (artifact["sha256"], artifact["size_bytes"]):
                raise ValueError("Artifact integrity check failed")
        except (OSError, ValueError) as error:
            errors.append(f"Artifact {artifact['id']}: {error}")
    by_id = {r["id"]: r for r in datasets}
    for run in runs:
        try:
            uuid.UUID(run["id"])
            manifest = json.loads(run["manifest"])
            dataset = by_id[run["dataset_id"]]
            if manifest["dataset_id"] != dataset["id"] or manifest["dataset_sha256"] != dataset["sha256"] or manifest["metadata_sha256"] != dataset["metadata_sha256"]:
                raise ValueError("Run provenance mismatch")
            copy = store.root / "runs" / run["id"] / "manifest.json"
            if copy.exists() and copy.read_bytes() != canonical(manifest):
                raise ValueError("Run manifest copy differs from catalog")
        except (OSError, ValueError, KeyError, ValidationError) as error:
            errors.append(f"Run {run['id']}: {error}")
    orphaned = [str(p.relative_to(store.root)) for p in (store.root / "objects").rglob("*") if p.is_file() and str(p.resolve()) not in referenced]
    return {"ok": not errors, "datasets": len(datasets), "runs": len(runs), "artifacts": len(artifacts), "errors": errors, "unreferenced_objects": sorted(orphaned)}


def backup(store, destination):
    destination = Path(destination).resolve()
    if destination.exists() or destination.is_relative_to(store.root):
        raise ValueError("Backup destination must be new and outside the storage root")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".backup-", dir=destination.parent))
    try:
        with store.connect() as source:
            target = sqlite3.connect(staging / "catalog.sqlite")
            try:
                source.backup(target)
            finally:
                target.close()
        snapshot = Store(staging)
        with snapshot.connect() as connection:
            objects = {row[0] for row in connection.execute("SELECT object_path FROM datasets UNION SELECT object_path FROM artifacts")}
            runs = [dict(r) for r in connection.execute("SELECT id,manifest FROM runs")]
        for relative in objects:
            incoming, outgoing = object_path(store, relative), object_path(snapshot, relative)
            outgoing.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(incoming, outgoing)
        for run in runs:
            uuid.UUID(run["id"])
            atomic_write(staging / "runs" / run["id"] / "manifest.json", canonical(json.loads(run["manifest"])))
        report = audit(snapshot)
        if not report["ok"]:
            raise ValueError(f"Backup audit failed: {report['errors']}")
        checksums = {p.relative_to(staging).as_posix(): file_digest(p)[0] for p in sorted(staging.rglob("*")) if p.is_file()}
        atomic_write(staging / "backup-checksums.json", canonical(checksums))
        staging.rename(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {"destination": str(destination), "audit": report}


def restore(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination.exists() or destination.is_relative_to(source):
        raise ValueError("Restore destination must be new and outside backup")
    checksums = json.loads((source / "backup-checksums.json").read_text())
    if "catalog.sqlite" not in checksums:
        raise ValueError("Backup catalog checksum is missing")
    for relative, sha in checksums.items():
        path = (source / relative).resolve()
        if not path.is_relative_to(source) or path == source or file_digest(path)[0] != sha:
            raise ValueError("Backup path or checksum is invalid")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".restore-", dir=destination.parent))
    try:
        for relative, sha in checksums.items():
            # Preserve the verified relative structure; never trust backup path spelling.
            incoming = (source / relative).resolve()
            outgoing = (staging / relative).resolve()
            if not outgoing.is_relative_to(staging):
                raise ValueError("Unsafe backup path")
            outgoing.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(incoming, outgoing)
            if file_digest(outgoing)[0] != sha:
                raise ValueError("Backup changed during restore")
        report = audit(Store(staging))
        if not report["ok"]:
            raise ValueError(f"Restored catalog audit failed: {report['errors']}")
        staging.rename(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {"destination": str(destination), "audit": report}
