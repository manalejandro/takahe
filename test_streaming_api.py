#!/usr/bin/env python
"""
Test script for the streaming API endpoint.
Usage: python test_streaming_api.py [stream_type]

stream_type can be: public, public:local, hashtag, user
"""
import sys
import requests
import time

def test_streaming(base_url="http://localhost:8000", stream_type="public", tag=None, token=None):
    """Test the streaming API endpoint."""
    url = f"{base_url}/api/v1/streaming"
    params = {"stream": stream_type}
    
    if tag:
        params["tag"] = tag
    
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    print(f"Connecting to streaming API...")
    print(f"URL: {url}")
    print(f"Stream: {stream_type}")
    print(f"Parameters: {params}")
    print("-" * 50)
    
    try:
        # Use stream=True to get Server-Sent Events
        response = requests.get(url, params=params, headers=headers, stream=True, timeout=60)
        
        if response.status_code != 200:
            print(f"Error: HTTP {response.status_code}")
            print(response.text)
            return
        
        print(f"Connected! (Status: {response.status_code})")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        print("-" * 50)
        print("Listening for events... (Press Ctrl+C to stop)")
        print()
        
        # Read and display events
        for line in response.iter_lines(decode_unicode=True):
            if line:
                print(line)
            
    except KeyboardInterrupt:
        print("\n\nDisconnected by user.")
    except requests.exceptions.Timeout:
        print("\n\nConnection timed out.")
    except Exception as e:
        print(f"\n\nError: {e}")


def test_health(base_url="http://localhost:8000"):
    """Test the health check endpoint."""
    url = f"{base_url}/api/v1/streaming/health"
    
    try:
        response = requests.get(url, timeout=5)
        print(f"Health check: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")


if __name__ == "__main__":
    # Parse command line arguments
    stream_type = "public"
    tag = None
    token = None
    
    if len(sys.argv) > 1:
        stream_type = sys.argv[1]
    
    if len(sys.argv) > 2:
        tag = sys.argv[2]
    
    if len(sys.argv) > 3:
        token = sys.argv[3]
    
    # Test health endpoint first
    print("Testing health endpoint...")
    test_health()
    print()
    
    # Test streaming
    test_streaming(stream_type=stream_type, tag=tag, token=token)
