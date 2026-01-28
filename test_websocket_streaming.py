#!/usr/bin/env python
"""
Test script for WebSocket streaming API endpoint.
Usage: python test_websocket_streaming.py [stream_type] [access_token]

stream_type can be: public, public:local, hashtag, user
Requires: pip install websockets
"""
import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    print("Error: websockets library not installed")
    print("Install with: pip install websockets")
    sys.exit(1)


async def test_websocket_streaming(
    base_url="ws://localhost:8000",
    stream_type="public",
    tag=None,
    access_token=None
):
    """Test the WebSocket streaming API endpoint."""
    
    # Build WebSocket URL
    if base_url.startswith("http://"):
        base_url = base_url.replace("http://", "ws://")
    elif base_url.startswith("https://"):
        base_url = base_url.replace("https://", "wss://")
    
    url = f"{base_url}/api/v1/streaming?stream={stream_type}"
    
    if tag:
        url += f"&tag={tag}"
    
    if access_token:
        url += f"&access_token={access_token}"
    
    print(f"Connecting to WebSocket...")
    print(f"URL: {url}")
    print(f"Stream: {stream_type}")
    print("-" * 50)
    
    try:
        async with websockets.connect(url) as websocket:
            print(f"✓ Connected!")
            print("-" * 50)
            print("Listening for events... (Press Ctrl+C to stop)")
            print()
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    event_type = data.get("event", "unknown")
                    
                    print(f"Event: {event_type}")
                    
                    if event_type == "update":
                        payload = json.loads(data["payload"])
                        account = payload.get("account", {})
                        content = payload.get("content", "")
                        
                        # Strip HTML tags for display
                        import re
                        content_text = re.sub('<[^<]+?>', '', content)
                        
                        print(f"  From: @{account.get('acct', 'unknown')}")
                        print(f"  Content: {content_text[:100]}...")
                    else:
                        print(f"  Data: {json.dumps(data, indent=2)}")
                    
                    print("-" * 50)
                    
                except json.JSONDecodeError as e:
                    print(f"Error decoding message: {e}")
                    print(f"Raw message: {message}")
                    
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"\n✗ Connection failed: HTTP {e.status_code}")
        if e.status_code == 401:
            print("  Authentication required or invalid token")
        elif e.status_code == 400:
            print("  Bad request - check parameters")
        elif e.status_code == 403:
            print("  Forbidden - insufficient permissions")
    except websockets.exceptions.WebSocketException as e:
        print(f"\n✗ WebSocket error: {e}")
    except KeyboardInterrupt:
        print("\n\nDisconnected by user.")
    except Exception as e:
        print(f"\n✗ Error: {e}")


if __name__ == "__main__":
    # Parse command line arguments
    stream_type = "public"
    tag = None
    access_token = None
    base_url = "ws://localhost:8000"
    
    if len(sys.argv) > 1:
        stream_type = sys.argv[1]
    
    if len(sys.argv) > 2:
        # Could be tag or token depending on stream type
        if stream_type.startswith("hashtag"):
            tag = sys.argv[2]
            if len(sys.argv) > 3:
                access_token = sys.argv[3]
        else:
            access_token = sys.argv[2]
    
    if len(sys.argv) > 3 and not tag:
        access_token = sys.argv[3]
    
    # Allow custom base URL via environment variable
    import os
    base_url = os.environ.get("TAKAHE_URL", base_url)
    
    print("WebSocket Streaming API Test")
    print("=" * 50)
    
    # Run the test
    asyncio.run(test_websocket_streaming(
        base_url=base_url,
        stream_type=stream_type,
        tag=tag,
        access_token=access_token,
    ))
