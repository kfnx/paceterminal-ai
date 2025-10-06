from celery import Celery

from app.core.config import settings

app = Celery(
    "tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

app.autodiscover_tasks(["app.tasks"])

from app.tasks import analysis_task #noqa
