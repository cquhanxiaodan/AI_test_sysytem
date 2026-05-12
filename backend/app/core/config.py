from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Gene Sequencer AI Test API"
    app_version: str = "0.1.0"
    environment: str = "local"

    database_url: str = Field(
        default="postgresql+psycopg://app:app@postgres:5432/gene_test"
    )
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_bucket: str = "gene-test-documents"
    local_storage_root: str = "storage"
    validation_plan_template_path: str = "templates/validation-plan-v1.docx"

    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
