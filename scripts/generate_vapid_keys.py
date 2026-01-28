#!/usr/bin/env python3
"""
Generate VAPID keys for Web Push Notifications.

VAPID (Voluntary Application Server Identification) keys are required for
Web Push Notifications. This script generates a public/private key pair
that can be used with Takahe.

Usage:
    python scripts/generate_vapid_keys.py

The keys can be added to your .env file:
    TAKAHE_VAPID_PUBLIC_KEY="<public_key>"
    TAKAHE_VAPID_PRIVATE_KEY="<private_key>"
"""

import sys

try:
    from py_vapid import Vapid
except ImportError:
    print("Error: py-vapid is required to generate VAPID keys.")
    print("Install it with: pip install py-vapid")
    sys.exit(1)


def generate_vapid_keys():
    """Generate and display VAPID key pair."""
    vapid = Vapid()
    vapid.generate_keys()
    
    # Use save_key() method to get the keys in the right format
    # This returns the keys in PEM format
    import io
    
    # Get private key
    private_buffer = io.BytesIO()
    vapid.save_key(private_buffer)
    private_key = private_buffer.getvalue().decode('utf-8').strip()
    
    # Get public key  
    public_buffer = io.BytesIO()
    vapid.save_public_key(public_buffer)
    public_key = public_buffer.getvalue().decode('utf-8').strip()
    
    print("=" * 70)
    print("VAPID Keys Generated Successfully!")
    print("=" * 70)
    print()
    print("Add these to your .env file or environment variables:")
    print()
    print(f'TAKAHE_VAPID_PUBLIC_KEY="{public_key}"')
    print(f'TAKAHE_VAPID_PRIVATE_KEY="{private_key}"')
    print()
    print("=" * 70)
    print("Keep your private key secret!")
    print("The public key is safe to share and will be sent to browsers.")
    print("=" * 70)


if __name__ == "__main__":
    generate_vapid_keys()
