"""Opaque artifact storage. Registered files are never deserialized or executed."""
import hashlib
import os
import tempfile
import uuid
from pathlib import Path

KINDS = {"raw_data", "weights", "architecture", "microscopy", "surface_metrology", "signal", "protocol", "report", "other"}


def file_digest(path):
    checksum = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
            size += len(chunk)
    return checksum.hexdigest(), size


def object_path(store, relative):
    path = (store.root / relative).resolve()
    if not path.is_relative_to(store.root / "objects"):
        raise ValueError("Object path is outside the object store")
    return path


def register(store, dataset_id, source, kind, description, media_type="application/octet-stream", run_id=None):
    if kind not in KINDS or not description.strip() or not media_type.strip():
        raise ValueError("Require a supported artifact kind, description, and media type")
    store.load(dataset_id)
    if run_id:
        with store.connect() as connection:
            run = connection.execute("SELECT dataset_id FROM runs WHERE id=?", (run_id,)).fetchone()
        if run is None or run["dataset_id"] != dataset_id:
            raise ValueError("Run must belong to the artifact dataset")
    source = Path(source)
    temporary_root = store.root / "objects"
    temporary_root.mkdir(exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".artifact-", dir=temporary_root)
    try:
        checksum, size = hashlib.sha256(), 0
        with source.open("rb") as incoming, os.fdopen(fd, "wb") as outgoing:
            fd = None
            for chunk in iter(lambda: incoming.read(1024 * 1024), b""):
                outgoing.write(chunk)
                checksum.update(chunk)
                size += len(chunk)
            outgoing.flush()
            os.fsync(outgoing.fileno())
        sha = checksum.hexdigest()
        relative = f"objects/{sha[:2]}/{sha}/artifact.bin"
        target = object_path(store, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and file_digest(target) != (sha, size):
            raise ValueError("Existing artifact object is corrupted")
        os.replace(temporary, target)
        identifier = str(uuid.uuid4())
        with store.connect() as connection:
            connection.execute("INSERT INTO artifacts(id,dataset_id,run_id,kind,original_name,media_type,description,sha256,size_bytes,object_path) VALUES(?,?,?,?,?,?,?,?,?,?)", (identifier, dataset_id, run_id, kind, source.name, media_type, description, sha, size, relative))
        return identifier
    finally:
        if fd is not None:
            os.close(fd)
        if os.path.exists(temporary):
            os.unlink(temporary)


def list_artifacts(store, dataset_id):
    with store.connect() as connection:
        return [dict(row) for row in connection.execute("SELECT * FROM artifacts WHERE dataset_id=? ORDER BY id", (dataset_id,))]


def retrieve(store, identifier, destination):
    with store.connect() as connection:
        row = connection.execute("SELECT * FROM artifacts WHERE id=?", (identifier,)).fetchone()
    if row is None:
        raise ValueError("Unknown artifact identifier")
    source = object_path(store, row["object_path"])
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidental overwrite. Remove partial output on failure.
    with destination.open("xb") as stream:
        try:
            with source.open("rb") as incoming:
                checksum, size = hashlib.sha256(), 0
                for chunk in iter(lambda: incoming.read(1024 * 1024), b""):
                    stream.write(chunk)
                    checksum.update(chunk)
                    size += len(chunk)
            if (checksum.hexdigest(), size) != (row["sha256"], row["size_bytes"]):
                raise ValueError("Artifact integrity check failed")
        except Exception:
            destination.unlink(missing_ok=True)
            raise
    return {"artifact_id": identifier, "destination": str(destination), "sha256": row["sha256"]}
