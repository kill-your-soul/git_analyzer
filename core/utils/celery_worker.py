import os

from celery import Celery

from core.config import settings

celery_app = Celery(
    "tasks",
    broker=settings.CELERY_BROKER,
    backend=settings.CELERY_BACKEND,
)

celery_app.autodiscover_tasks(["utils.download"])
# celery_app.conf.update(
#     event_serializer='pickle',
#     result_serializer='json',
#     accept_content=['pickle', 'json'],
# )