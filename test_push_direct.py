#!/usr/bin/env python3
"""
Test directo de la lógica de push subscription
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'takahe.settings')
django.setup()

from pydantic import BaseModel

# Recreate the schema exactly as in token.py
class PushSubscriptionSchema(BaseModel):
    """
    Basic validating schema for push data
    """

    class Keys(BaseModel):
        p256dh: str
        auth: str

    endpoint: str
    keys: Keys
    alerts: dict[str, bool]
    policy: str


# Simulate what create_subscription does
print("=" * 70)
print("TESTING PUSH SUBSCRIPTION SERIALIZATION")
print("=" * 70)

# This is what create_subscription builds
subscription_data = {
    "endpoint": "https://updates.push.services.mozilla.com/wpush/v2/test123",
    "keys": {
        "p256dh": "BK4SLmHT1hHwX1V...",
        "auth": "gEfK3BF..."
    },
    "alerts": {
        "mention": True,
        "status": True,
        "reblog": True,
        "follow": True,
        "follow_request": True,
        "favourite": True,
        "poll": True,
        "update": True,
        "admin_sign_up": False,
        "admin_report": False,
    },
    "policy": "all"
}

print("\n1. Input data:")
print(f"   Type: {type(subscription_data)}")
print(f"   Keys: {list(subscription_data.keys())}")
print(f"   keys type: {type(subscription_data['keys'])}")

# Validate with Pydantic
print("\n2. Creating Pydantic model...")
try:
    validated = PushSubscriptionSchema(**subscription_data)
    print(f"   ✅ Validation successful")
    print(f"   Type: {type(validated)}")
except Exception as e:
    print(f"   ❌ Validation failed: {e}")
    exit(1)

# Convert to dict (this is what token.py does)
print("\n3. Converting to dict...")
try:
    result = validated.dict()
    print(f"   ✅ .dict() successful")
    print(f"   Type: {type(result)}")
    print(f"   Keys: {list(result.keys())}")
    print(f"   keys type: {type(result['keys'])}")
    print(f"   keys.p256dh: {result['keys']['p256dh']}")
    print(f"   keys.auth: {result['keys']['auth']}")
except Exception as e:
    print(f"   ❌ .dict() failed: {e}")
    exit(1)

# Test saving to database
print("\n4. Testing database save...")
try:
    from api.models import Token, Application
    from users.models import Identity, User
    
    # Find a token to test with
    token = Token.objects.first()
    if not token:
        print("   ⚠️  No tokens in database to test with")
    else:
        print(f"   Found token {token.id}")
        print(f"   Current push_subscription: {token.push_subscription}")
        
        # Try to set it
        print(f"\n   Setting push_subscription...")
        token.push_subscription = result
        token.save()
        print(f"   ✅ Saved")
        
        # Verify
        token.refresh_from_db()
        print(f"   After refresh: {token.push_subscription}")
        
        if token.push_subscription:
            print(f"   ✅ SUCCESS! push_subscription was saved")
        else:
            print(f"   ❌ FAILED! push_subscription is still null")
            
except Exception as e:
    print(f"   ❌ Database test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
