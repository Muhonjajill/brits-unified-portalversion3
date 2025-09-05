import os
import django

# Ensure settings are configured first
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "unified_portal.settings")

# Initialize Django to make sure apps are loaded
django.setup()

# Now import Django and Channels components
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Import routing after settings configuration
import core.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(core.routing.websocket_urlpatterns)
    ),
})
