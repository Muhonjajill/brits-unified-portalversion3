import os
from celery import Celery
from celery.schedules import crontab   # <-- add this

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "unified_portal.settings")

app = Celery("unified_portal")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

