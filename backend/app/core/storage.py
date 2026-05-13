from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path

from minio import Minio
from minio.error import S3Error

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


class MinioStorageBackend(StorageBackend):
    def __init__(self) -> None:
        settings = get_settings()
        self.bucket = settings.minio_bucket
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def put_bytes(self, key: str, content: bytes) -> str:
        self.client.put_object(self.bucket, key, BytesIO(content), len(content))
        return f"minio://{self.bucket}/{key}"

    def get_bytes(self, storage_path: str) -> bytes | None:
        prefix = f"minio://{self.bucket}/"
        if not storage_path.startswith(prefix):
            return None
        object_name = storage_path.removeprefix(prefix)
        try:
            response = self.client.get_object(self.bucket, object_name)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()
        except S3Error:
            return None


def get_storage_backend() -> StorageBackend:
    settings = get_settings()
    if settings.storage_backend == "minio":
        return MinioStorageBackend()
    return LocalStorageBackend(settings.local_storage_root)
