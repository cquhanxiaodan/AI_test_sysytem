from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import get_settings


class StorageBackend(ABC):
    @abstractmethod
    def put_bytes(self, key: str, content: bytes) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_bytes(self, storage_path: str) -> bytes | None:
        raise NotImplementedError


class LocalStorageBackend(StorageBackend):
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def put_bytes(self, key: str, content: bytes) -> str:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return str(path)

    def get_bytes(self, storage_path: str) -> bytes | None:
        path = Path(storage_path)
        if not path.exists():
            return None
        return path.read_bytes()


def get_storage_backend() -> StorageBackend:
    settings = get_settings()
    return LocalStorageBackend(settings.local_storage_root)
