import asyncio
import json
import time
from typing import AsyncGenerator

from asgiref.sync import sync_to_async
from django.http import HttpRequest, HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from activities.models import Post, TimelineEvent
from activities.services import TimelineService
from api import schemas
from core.models import Config


async def event_stream_generator(
    request: HttpRequest,
    stream_type: str,
    hashtag: str | None = None,
    list_id: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    Generator that yields Server-Sent Events for the streaming API.
    """
    # Send initial connection event
    yield f": connected to {stream_type} stream\n\n"

    # Get identity safely
    identity = getattr(request, 'identity', None)
    
    last_event_id = None
    check_interval = 2.0  # Check for new events every 2 seconds
    ping_interval = 15  # Send ping every 15 seconds
    last_ping = time.time()

    try:
        while True:
            current_time = time.time()
            
            # Determine which timeline to query based on stream type
            queryset = None
            
            if stream_type == "user":
                if not identity:
                    break
                queryset = TimelineService(identity).home()
            elif stream_type == "public":
                queryset = TimelineService(identity).federated()
            elif stream_type == "public:local":
                queryset = TimelineService(identity).local()
            elif stream_type == "hashtag" and hashtag:
                queryset = TimelineService(identity).hashtag(hashtag.lower())
            elif stream_type == "hashtag:local" and hashtag:
                queryset = TimelineService(identity).hashtag(hashtag.lower()).filter(local=True)
            elif stream_type == "list" and list_id:
                # List timeline not fully implemented yet
                await asyncio.sleep(check_interval)
                continue

            if queryset is None:
                break

            # Get new events since last check
            if stream_type == "user":
                # For user timeline, we get TimelineEvents
                queryset = queryset.select_related(
                    "subject_post",
                    "subject_post__author",
                    "subject_post__author__domain",
                ).prefetch_related(
                    "subject_post__attachments",
                    "subject_post__mentions",
                    "subject_post__mentions__domain",
                    "subject_post__emojis",
                )
                
                if last_event_id:
                    queryset = queryset.filter(id__gt=int(last_event_id))
                
                events = await sync_to_async(list)(queryset.order_by("id")[:20])
                
                for event in events:
                    last_event_id = str(event.id)
                    
                    # Handle different event types
                    if event.type == TimelineEvent.Types.post:
                        status_data = schemas.Status.from_post(
                            event.subject_post,
                            identity=identity,
                        )
                        payload = json.dumps(status_data.dict())
                        yield f"event: update\ndata: {payload}\n\n"
                    elif event.type == TimelineEvent.Types.boost:
                        status_data = schemas.Status.from_post(
                            event.subject_post,
                            identity=identity,
                        )
                        payload = json.dumps(status_data.dict())
                        yield f"event: update\ndata: {payload}\n\n"
            else:
                # For public/hashtag timelines, we get Posts
                queryset = queryset.select_related(
                    "author",
                    "author__domain",
                ).prefetch_related(
                    "attachments",
                    "mentions",
                    "mentions__domain",
                    "emojis",
                )
                
                if last_event_id:
                    queryset = queryset.filter(id__gt=int(last_event_id))
                
                posts = await sync_to_async(list)(queryset.order_by("id")[:20])
                
                for post in posts:
                    last_event_id = str(post.id)
                    status_data = schemas.Status.from_post(
                        post,
                        identity=identity,
                    )
                    payload = json.dumps(status_data.dict())
                    yield f"event: update\ndata: {payload}\n\n"

            # Send periodic ping to keep connection alive
            if current_time - last_ping >= ping_interval:
                yield ": ping\n\n"
                last_ping = current_time
            
            # Wait before checking for new events
            await asyncio.sleep(check_interval)

    except GeneratorExit:
        # Client disconnected
        pass
    except Exception as e:
        # Log error and close connection
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"


@csrf_exempt
@require_http_methods(["GET"])
def streaming(request: HttpRequest) -> StreamingHttpResponse | JsonResponse:
    """
    WebSocket-alternative streaming API endpoint using Server-Sent Events.
    
    Supported streams:
    - user: Events for the authenticated user (home timeline and notifications)
    - public: Public timeline
    - public:local: Local public timeline
    - hashtag: Updates for a specific hashtag (requires 'tag' parameter)
    - hashtag:local: Updates for a local hashtag (requires 'tag' parameter)
    - list: Updates for a specific list (requires 'list' parameter)
    """
    # Get parameters
    stream = request.GET.get("stream")
    tag = request.GET.get("tag")
    list_id = request.GET.get("list")
    
    # Validate stream parameter
    if not stream:
        return JsonResponse({"error": "stream parameter is required"}, status=400)
    
    valid_streams = ["user", "public", "public:local", "hashtag", "hashtag:local", "list"]
    if stream not in valid_streams:
        return JsonResponse(
            {"error": f"Invalid stream type. Must be one of: {', '.join(valid_streams)}"},
            status=400,
        )
    
    # Validate required parameters for specific streams
    if stream in ["hashtag", "hashtag:local"] and not tag:
        return JsonResponse({"error": "tag parameter is required for hashtag streams"}, status=400)
    
    if stream == "list" and not list_id:
        return JsonResponse({"error": "list parameter is required for list stream"}, status=400)
    
    # Get identity safely
    identity = getattr(request, 'identity', None)
    token = getattr(request, 'token', None)
    
    # User stream requires authentication
    if stream == "user":
        if not identity:
            return JsonResponse({"error": "Authentication required for user stream"}, status=401)
        
        # Check scope
        if token and not token.has_scope("read:statuses"):
            return JsonResponse({"error": "Insufficient scope"}, status=403)
    
    # Public streams might be disabled
    if stream.startswith("public"):
        if not identity and not Config.system.public_timeline:
            return JsonResponse({"error": "Public timeline is disabled"}, status=422)
    
    # Create streaming response with SSE headers
    response = StreamingHttpResponse(
        event_stream_generator(request, stream, hashtag=tag, list_id=list_id),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    
    return response


@csrf_exempt
@require_http_methods(["GET"])
def health(request: HttpRequest) -> JsonResponse:
    """
    Health check endpoint for the streaming service.
    """
    return JsonResponse({"status": "ok"})
