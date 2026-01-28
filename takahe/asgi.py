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
    
    CRITICAL: This must intercept streaming endpoint for BOTH http AND websocket
    because Django's URL routing will process /api/v1/streaming as HTTP otherwise.
    """
    path = scope.get("path", "")
    scope_type = scope["type"]
    
    print(f"[ASGI Router] Request type: {scope_type}, path: {path}")
    
    # Handle streaming endpoint - must check BEFORE Django HTTP routing
    if path == "/api/v1/streaming":
        if scope_type == "websocket":
            print(f"[ASGI Router] Routing to WebSocket handler")
            await streaming_websocket(scope, receive, send)
            return
        else:
            # If uvicorn doesn't have websockets library, it treats WebSocket as HTTP
            # This should not happen if uvicorn[standard] is installed
            print(f"[ASGI Router] WARNING: /api/v1/streaming received as {scope_type}, not websocket")
            print(f"[ASGI Router] This means uvicorn doesn't have WebSocket support installed")
            print(f"[ASGI Router] Install with: pip install 'uvicorn[standard]'")
            # Return error to client
            await send({
                "type": "http.response.start",
                "status": 500,
                "headers": [[b"content-type", b"application/json"]],
            })
            await send({
                "type": "http.response.body",
                "body": b'{"error": "WebSocket support not available. Contact server administrator."}',
            })
            return
    
    # Handle WebSocket connections to unknown paths
    if scope_type == "websocket":
        print(f"[ASGI Router] Unknown WebSocket path: {path}, closing connection")
        await send({
            "type": "websocket.close",
            "code": 4404,
        })
        return
    
    # Handle all other HTTP requests with Django
    await django_asgi_app(scope, receive, send)
