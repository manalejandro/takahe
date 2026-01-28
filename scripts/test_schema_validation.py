#!/usr/bin/env python3
"""
Script para probar la creación de push subscriptions localmente.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "takahe.settings")
django.setup()

from api.models.token import PushSubscriptionSchema

# Test data similar to what Elk sends
test_data = {
    "endpoint": "https://fcm.googleapis.com/fcm/send/test-endpoint",
    "keys": {
        "p256dh": "BKJ...test_p256dh_key...",
        "auth": "abc...test_auth_key..."
    },
    "alerts": {
        "mention": True,
        "status": False,
        "reblog": True,
        "follow": True,
        "follow_request": False,
        "favourite": False,
        "poll": False,
        "update": False,
        "admin_sign_up": False,
        "admin_report": False,
    },
    "policy": "all"
}

print("=" * 70)
print("Testing PushSubscriptionSchema validation")
print("=" * 70)

try:
    print("\n1. Creating schema instance...")
    schema = PushSubscriptionSchema(**test_data)
    print("✅ Schema instance created successfully")
    print(f"   Endpoint: {schema.endpoint}")
    print(f"   Policy: {schema.policy}")
    print(f"   Keys: p256dh={schema.keys.p256dh[:20]}..., auth={schema.keys.auth[:20]}...")
    
    print("\n2. Converting to dict...")
    result_dict = schema.dict()
    print("✅ Converted to dict successfully")
    print(f"   Type: {type(result_dict)}")
    print(f"   Keys in dict: {list(result_dict.keys())}")
    
    print("\n3. Verifying structure...")
    assert "endpoint" in result_dict
    assert "keys" in result_dict
    assert "alerts" in result_dict
    assert "policy" in result_dict
    assert isinstance(result_dict["keys"], dict)
    assert isinstance(result_dict["alerts"], dict)
    assert "p256dh" in result_dict["keys"]
    assert "auth" in result_dict["keys"]
    print("✅ Structure is correct")
    
    print("\n4. JSON serialization test...")
    import json
    json_str = json.dumps(result_dict)
    print("✅ Can be serialized to JSON")
    print(f"   JSON length: {len(json_str)} bytes")
    
    print("\n" + "=" * 70)
    print("✅ All tests passed!")
    print("=" * 70)
    print("\nThe schema validation works correctly.")
    print("If push_subscription is still null, the issue is elsewhere.")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
