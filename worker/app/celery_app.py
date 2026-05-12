from celery import Celery

from app.core.config import get_settings


settings = get_settings()

celery_app = Celery(
    "gene_sequencer_ai_test_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

celery_app.autodiscover_tasks(["worker_app.tasks"])
