"""Provider-neutral original-object storage boundary."""

import hashlib
import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class StoredObject:
    key: str
    etag: str
    size: int


class ObjectStorage(Protocol):
    def put(self, key: str, content: bytes) -> StoredObject: ...
    def read(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...
    def exists(self, key: str) -> bool: ...
    def materialize(self, key: str): ...


class LocalObjectStorage:
    """Durable local adapter retained for the current single-node deployment."""
    def __init__(self, root: Path): self.root = root
    def path(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        root = self.root.resolve()
        if root not in candidate.parents:
            raise ValueError("Storage key escapes configured root")
        return candidate
    def put(self, key: str, content: bytes) -> StoredObject:
        destination = self.path(key); destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=".upload-", dir=destination.parent)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content); handle.flush(); os.fsync(handle.fileno())
            os.replace(temporary, destination)
        finally:
            Path(temporary).unlink(missing_ok=True)
        return StoredObject(key, hashlib.sha256(content).hexdigest(), len(content))
    def read(self, key: str) -> bytes: return self.path(key).read_bytes()
    def delete(self, key: str) -> None: self.path(key).unlink(missing_ok=True)
    def exists(self, key: str) -> bool: return self.path(key).is_file()
    @contextmanager
    def materialize(self, key: str):
        yield self.path(key)


class S3CompatibleObjectStorage:
    """Explicit adapter boundary; activation requires an owner-selected signed client."""
    def __init__(self, *_, **__):
        raise RuntimeError("S3-compatible storage requires configured endpoint, bucket and credentials")
