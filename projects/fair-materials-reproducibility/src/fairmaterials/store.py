"""Local catalog with immutable, content-addressed snapshots."""
import json
import os
import sqlite3
import tempfile
import uuid
from contextlib import contextmanager
from importlib.resources import files
from pathlib import Path

from .data import canonical, digest, validate


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(files("fairmaterials").joinpath("schema.sql").read_text())

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.root / "catalog.sqlite")
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def ingest(self, csv_path, metadata_path):
        raw = Path(csv_path).read_bytes()
        metadata = json.loads(Path(metadata_path).read_text())
        validate(metadata, raw)
        identifier, sha = metadata["identifier"], digest(raw)
        meta_raw = canonical(metadata)
        with self.connect() as connection:
            old = connection.execute("SELECT * FROM datasets WHERE id=?", (identifier,)).fetchone()
            if old:
                if old["sha256"] != sha or old["metadata_sha256"] != digest(meta_raw):
                    raise ValueError("Identifier already registered with different content; mint a new UUID")
                self.load(identifier)
                return identifier
            relative = f"objects/{sha[:2]}/{sha}/materials.csv"
            destination = self.root / relative
            if destination.exists() and digest(destination.read_bytes()) != sha:
                raise ValueError("Existing object is corrupted")
            atomic_write(destination, raw)
            connection.execute("INSERT INTO datasets(id,title,metadata,sha256,metadata_sha256,object_path) VALUES(?,?,?,?,?,?)", (identifier, metadata["title"], meta_raw.decode(), sha, digest(meta_raw), relative))
        return identifier

    def load(self, identifier):
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM datasets WHERE id=?", (identifier,)).fetchone()
        if row is None:
            raise ValueError("Unknown dataset identifier")
        from .artifacts import object_path
        raw = object_path(self, row["object_path"]).read_bytes()
        if digest(raw) != row["sha256"] or digest(row["metadata"].encode()) != row["metadata_sha256"]:
            raise ValueError("Dataset integrity check failed")
        metadata = json.loads(row["metadata"])
        return dict(row), metadata, raw, validate(metadata, raw)

    def search(self, query="", material=None, data_kind=None):
        with self.connect() as connection:
            return [dict(row) for row in connection.execute("SELECT id,title,sha256 FROM datasets WHERE instr(lower(title || metadata),lower(?)) > 0 AND (? IS NULL OR json_extract(metadata, '$.experiment.material')=?) AND (? IS NULL OR json_extract(metadata, '$.provenance.kind')=?) ORDER BY id", (query, material, material, data_kind, data_kind))]

    def record_run(self, dataset_id, manifest):
        run_id = str(uuid.uuid4())
        with self.connect() as connection:
            connection.execute("INSERT INTO runs(id,dataset_id,manifest) VALUES(?,?,?)", (run_id, dataset_id, canonical(manifest).decode()))
        return run_id
