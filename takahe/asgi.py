"""
ASGI config for takahe project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "takahe.settings")

# Get Django ASGI application - this initializes Django automatically
django_asgi_app = get_asgi_application()

# Import WebSocket handler after Django ASGI app is created
from api.websocket_streaming import streaming_websocket


async def application(scope, receive, send):
    """
    Main ASGI application that routes to HTTP or WebSocket handlers.
    """
    print(f"[ASGI Router] Request type: {scope['type']}, path: {scope.get('path', 'N/A')}")
    
    if scope["type"] == "websocket":
        # Check if this is a streaming endpoint
        path = scope.get("path", "")
        if path == "/api/v1/streaming":
            print(f"[ASGI Router] Routing to WebSocket handler")
            await streaming_websocket(scope, receive, send)
        else:
            # Close unknown WebSocket connections
            print(f"[ASGI Router] Unknown WebSocket path: {path}")
            await send({
                "type": "websocket.close",
                "code": 4404,
            })
    else:
        # Handle HTTP requests with Django
        await django_asgi_app(scope, receive, send)
