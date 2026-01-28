#!/usr/bin/env python
"""
Test script to verify access token for WebSocket streaming
"""
import os
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "takahe.settings")
django.setup()

from api.models import Token

# The token from the error message
test_token = "HVNczap2acmqgqfIuJeGb5gMx0oa-ClaX8hUfHzey9IqdZ0RxkFFBsPhvw"

print("=" * 70)
print("WEBSOCKET TOKEN VERIFICATION")
print("=" * 70)
print(f"\nToken to test: {test_token[:20]}...\n")

try:
    token = Token.objects.select_related("identity").get(
        token=test_token,
        revoked__isnull=True,
    )
    print("✅ TOKEN FOUND AND VALID!")
    print(f"   Identity: {token.identity.handle}")
    print(f"   Identity ID: {token.identity.id}")
    print(f"   Created: {token.created}")
    print(f"   Scopes: {token.scopes}")
    print(f"   Has read:statuses scope: {token.has_scope('read:statuses')}")
    print()
    
    # Test if identity exists
    if token.identity:
        print(f"✅ Identity is valid: {token.identity.handle}")
        print(f"   Local: {token.identity.local}")
        print(f"   Domain: {token.identity.domain}")
    else:
        print("❌ Identity is NULL - THIS IS A PROBLEM!")
    
except Token.DoesNotExist:
    print("❌ TOKEN NOT FOUND OR REVOKED!")
    print("\nPossible reasons:")
    print("  1. Token has been revoked")
    print("  2. Token doesn't exist in database")
    print("  3. Token string is incorrect")
    
    # Check if token exists but is revoked
    try:
        revoked_token = Token.objects.get(token=test_token)
        print(f"\n⚠️  Token exists but is REVOKED at: {revoked_token.revoked}")
    except Token.DoesNotExist:
        print("\n⚠️  Token does not exist in database at all")
        
except Exception as e:
    print(f"❌ ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
print("DIAGNOSTIC COMPLETE")
print("=" * 70)
