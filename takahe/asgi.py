"""
ASGI config for takahe project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "takahe.settings")

# Get Django ASGI application early to populate apps registry
django_asgi_app = get_asgi_application()

# Import WebSocket handler after Django is initialized
from api.websocket_streaming import streaming_websocket


async def application(scope, receive, send):
    """
    Main ASGI application that routes to HTTP or WebSocket handlers.
    """
    if scope["type"] == "websocket":
        # Check if this is a streaming endpoint
        path = scope.get("path", "")
        if path == "/api/v1/streaming":
            await streaming_websocket(scope, receive, send)
        else:
            # Close unknown WebSocket connections
            await send({
                "type": "websocket.close",
                "code": 4404,
            })
    else:
        # Handle HTTP requests with Django
        await django_asgi_app(scope, receive, send)
