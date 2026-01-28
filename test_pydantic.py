#!/usr/bin/env python3
"""
Test simple para verificar serialización de Pydantic v1
"""

from pydantic import BaseModel

class Keys(BaseModel):
    p256dh: str
    auth: str

class PushSubscriptionSchema(BaseModel):
    endpoint: str
    keys: Keys
    alerts: dict
    policy: str

# Test data
test_data = {
    "endpoint": "https://example.com/push",
    "keys": {
        "p256dh": "test_p256dh",
        "auth": "test_auth"
    },
    "alerts": {
        "mention": True,
        "follow": False
    },
    "policy": "all"
}

print("Testing Pydantic v1 serialization...")
print("=" * 60)

# Create instance
schema = PushSubscriptionSchema(**test_data)
print("✅ Schema created")

# Try .dict()
try:
    result = schema.dict()
    print("✅ .dict() works")
    print(f"   Type: {type(result)}")
    print(f"   Keys: {list(result.keys())}")
    print(f"   keys.p256dh: {result['keys']['p256dh']}")
    print(f"   keys.auth: {result['keys']['auth']}")
except Exception as e:
    print(f"❌ .dict() failed: {e}")

print("\n" + "=" * 60)
print("Result:", "SUCCESS" if result else "FAILED")
