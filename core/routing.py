# core/routing.py

from django.urls import re_path
from .consumers import EscalationConsumer

websocket_urlpatterns = [
    re_path(r"ws/escalations/$", EscalationConsumer.as_asgi()),
]