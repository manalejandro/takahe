import asyncio
import json
import time
from urllib.parse import parse_qs, urlparse

from asgiref.sync import sync_to_async

from activities.models import TimelineEvent
from activities.services import TimelineService
from api import schemas
from api.models import Token
from core.models import Config


@sync_to_async
def get_token_and_identity(access_token):
    """
    Fetch token and identity from database.
    Must be a separate function for sync_to_async to work properly.
    """
    try:
        token = Token.objects.select_related("identity").get(
            token=access_token,
            revoked__isnull=True,
        )
        print(f"✓ Token found: {token.token[:20]}... for identity: {token.identity.handle}")
        return token, token.identity
    except Token.DoesNotExist:
        print(f"✗ Token not found: {access_token[:20]}...")
        return None, None
    except Exception as e:
        print(f"✗ Token query error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None, None


@sync_to_async
def check_public_timeline_enabled():
    """Check if public timeline is enabled."""
    try:
        return Config.system.public_timeline
    except Exception as e:
        print(f"✗ Config query error: {e}")
        return False


async def streaming_websocket(scope, receive, send):
    """
    WebSocket handler for Mastodon streaming API.
    
    Handles WebSocket connections at /api/v1/streaming
    """
    # CRITICAL: Accept WebSocket FIRST before any validation
    await send({
        "type": "websocket.accept",
    })
    
    # Parse query string
    query_string = scope.get("query_string", b"").decode("utf-8")
    params = parse_qs(query_string)
    
    # Get parameters
    stream = params.get("stream", [None])[0]
    tag = params.get("tag", [None])[0]
    list_id = params.get("list", [None])[0]
    access_token = params.get("access_token", [None])[0]
    
    # Validate stream parameter
    if not stream:
        await send({
            "type": "websocket.close",
            "code": 4400,
            "reason": "stream parameter is required",
        })
        return
    
    valid_streams = ["user", "public", "public:local", "hashtag", "hashtag:local", "list"]
    if stream not in valid_streams:
        await send({
            "type": "websocket.close",
            "code": 4400,
            "reason": f"Invalid stream type",
        })
        return
    
    # Validate required parameters
    if stream in ["hashtag", "hashtag:local"] and not tag:
        await send({
            "type": "websocket.close",
            "code": 4400,
            "reason": "tag parameter required",
        })
        return
    
    if stream == "list" and not list_id:
        await send({
            "type": "websocket.close",
            "code": 4400,
            "reason": "list parameter required",
        })
        return
    
    # Authenticate
    identity = None
    token = None
    
    if access_token:
        print(f"Attempting to authenticate with token: {access_token[:20]}...")
        token, identity = await get_token_and_identity(access_token)
        
        if token is None:
            print(f"WebSocket auth failed: Token validation failed")
            await send({
                "type": "websocket.close",
                "code": 4401,
                "reason": "Invalid access token",
            })
            return
        
        print(f"✓ Authenticated as: {identity.handle} (ID: {identity.id})")
    else:
        print("No access_token provided in query string")
    
    # Check authentication requirements
    if stream == "user":
        if not identity:
            await send({
                "type": "websocket.close",
                "code": 4401,
                "reason": "Authentication required",
            })
            return
        
        if token and not token.has_scope("read:statuses"):
            await send({
                "type": "websocket.close",
                "code": 4403,
                "reason": "Insufficient scope",
            })
            return
    
    # Check if public timeline is enabled
    if stream.startswith("public"):
        public_timeline_enabled = await check_public_timeline_enabled()
        
        if not identity and not public_timeline_enabled:
            print("Public timeline is disabled and no authentication provided")
            await send({
                "type": "websocket.close",
                "code": 4422,
                "reason": "Public timeline disabled",
            })
            return
    
    print(f"✓ All validations passed, starting WebSocket streaming for: {stream}")
    
    # Start streaming events
    try:
        await stream_events(send, receive, stream, identity, tag, list_id)
    except Exception as e:
        # Log error
        print(f"WebSocket streaming error: {e}")
    finally:
        # Close connection
        try:
            await send({
                "type": "websocket.close",
                "code": 1000,
            })
        except:
            pass


async def stream_events(send, receive, stream_type, identity, hashtag=None, list_id=None):
    """
    Stream events to the WebSocket client.
    """
    last_event_id = None
    check_interval = 2.0  # Check for new events every 2 seconds
    
    # Task to handle incoming messages (mostly for connection checks)
    async def handle_incoming():
        while True:
            try:
                message = await receive()
                if message["type"] == "websocket.disconnect":
                    break
            except:
                break
    
    # Start incoming message handler
    incoming_task = asyncio.create_task(handle_incoming())
    
    try:
        while True:
            # Determine which timeline to query
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
            
            # Get new events
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
                
                # Execute query synchronously (Django ORM is not async-safe by default)
                events = await asyncio.to_thread(
                    lambda: list(queryset.order_by("id")[:20])
                )
                
                for event in events:
                    last_event_id = str(event.id)
                    
                    # Handle different event types
                    if event.type == TimelineEvent.Types.post:
                        status_data = await asyncio.to_thread(
                            schemas.Status.from_post,
                            event.subject_post,
                            identity=identity,
                        )
                        payload = {
                            "event": "update",
                            "payload": json.dumps(status_data.dict()),
                        }
                        await send({
                            "type": "websocket.send",
                            "text": json.dumps(payload),
                        })
                    elif event.type == TimelineEvent.Types.boost:
                        status_data = await asyncio.to_thread(
                            schemas.Status.from_post,
                            event.subject_post,
                            identity=identity,
                        )
                        payload = {
                            "event": "update",
                            "payload": json.dumps(status_data.dict()),
                        }
                        await send({
                            "type": "websocket.send",
                            "text": json.dumps(payload),
                        })
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
                
                # Execute query synchronously
                posts = await asyncio.to_thread(
                    lambda: list(queryset.order_by("id")[:20])
                )
                
                for post in posts:
                    last_event_id = str(post.id)
                    status_data = await asyncio.to_thread(
                        schemas.Status.from_post,
                        post,
                        identity=identity,
                    )
                    payload = {
                        "event": "update",
                        "payload": json.dumps(status_data.dict()),
                    }
                    await send({
                        "type": "websocket.send",
                        "text": json.dumps(payload),
                    })
            
            # Wait before checking for new events
            await asyncio.sleep(check_interval)
    
    finally:
        # Cancel incoming task
        incoming_task.cancel()
        try:
            await incoming_task
        except asyncio.CancelledError:
            pass
