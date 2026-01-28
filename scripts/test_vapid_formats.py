#!/usr/bin/env python3
"""
Test complete push notification flow with correct key formats.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'takahe.settings')
django.setup()

from django.conf import settings
from core.vapid_utils import (
    get_vapid_public_key_for_browser,
    get_vapid_private_key_for_pywebpush,
)

print("=" * 70)
print("VAPID KEY FORMAT TEST")
print("=" * 70)

# Test 1: Check raw keys
print("\n1. Raw keys from settings:")
print(f"   Public (base64url): {settings.SETUP.VAPID_PUBLIC_KEY[:40]}...")
print(f"   Private (base64url): {settings.SETUP.VAPID_PRIVATE_KEY[:40]}...")

# Test 2: Public key for browser (should be base64url)
print("\n2. Public key for browser (base64url format):")
browser_key = get_vapid_public_key_for_browser()
print(f"   Length: {len(browser_key)} chars")
print(f"   Starts with 'B': {browser_key[0] == 'B'}")
print(f"   Key: {browser_key[:40]}...")

# Test 3: Private key for pywebpush (should be PEM)
print("\n3. Private key for pywebpush (PEM format):")
try:
    pem_key = get_vapid_private_key_for_pywebpush()
    print(f"   Is PEM: {pem_key.startswith('-----BEGIN')}")
    print(f"   First line: {pem_key.split()[0]}")
    print(f"   Length: {len(pem_key)} chars")
except Exception as e:
    print(f"   ERROR: {e}")

# Test 4: Try to use with pywebpush
print("\n4. Test with pywebpush:")
try:
    from pywebpush import webpush
    
    # Dummy subscription
    test_subscription = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/dummy",
        "keys": {
            "p256dh": "BKU1B_c_8DFPUXjgQNsNFi6MIrn5rzTh3d5CGo7NOpsIF-MY4qowgHU1Y_YAFAjNOTS5L9X2u8tBM3w4LxcEijU",
            "auth": "dummyauthkey123"
        }
    }
    
    # This will fail to actually send (bad endpoint) but will validate the keys
    try:
        webpush(
            subscription_info=test_subscription,
            data='{"test": true}',
            vapid_private_key=pem_key,
            vapid_claims={"sub": "mailto:test@example.com"},
            timeout=0.1  # Short timeout since endpoint is fake
        )
    except Exception as e:
        # Expected to fail, but check if it's a key error or connection error
        error_msg = str(e).lower()
        if 'key' in error_msg or 'pem' in error_msg or 'format' in error_msg:
            print(f"   ERROR: Key format issue - {e}")
        else:
            print(f"   OK: Keys are valid (connection error expected: {type(e).__name__})")
            
except Exception as e:
    print(f"   ERROR: {e}")

# Test 5: Check URL-safe characters in browser key
print("\n5. Browser key validation:")
browser_key = get_vapid_public_key_for_browser()
has_urlsafe = '-' in browser_key or '_' in browser_key
has_unsafe = '+' in browser_key or '/' in browser_key
print(f"   Has URL-safe chars (- or _): {has_urlsafe}")
print(f"   Has unsafe chars (+ or /): {has_unsafe}")
print(f"   ✓ Correct format" if has_urlsafe and not has_unsafe else "   ✗ Wrong format")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
