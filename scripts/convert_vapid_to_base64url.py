#!/usr/bin/env python3
"""
Convert PEM VAPID keys to base64url format (as used by Web Push spec).
"""

import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_public_key, load_pem_private_key

def pem_to_base64url(pem_path, key_type='public'):
    """Convert PEM key to base64url format."""
    with open(pem_path, 'rb') as f:
        pem_data = f.read()
    
    if key_type == 'public':
        key = load_pem_public_key(pem_data)
        # Get raw public key bytes (uncompressed point format)
        raw_bytes = key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )
    else:  # private
        key = load_pem_private_key(pem_data, password=None)
        # Get raw private key bytes
        raw_bytes = key.private_numbers().private_value.to_bytes(32, byteorder='big')
    
    # Convert to base64url (without padding)
    base64url = base64.urlsafe_b64encode(raw_bytes).decode('ascii').rstrip('=')
    return base64url

if __name__ == "__main__":
    public_key = pem_to_base64url('/tmp/vapid_public.pem', 'public')
    private_key = pem_to_base64url('/tmp/vapid_private.pem', 'private')
    
    print("=" * 70)
    print("VAPID Keys in base64url format (for Takahe):")
    print("=" * 70)
    print()
    print(f'TAKAHE_VAPID_PUBLIC_KEY="{public_key}"')
    print(f'TAKAHE_VAPID_PRIVATE_KEY="{private_key}"')
    print()
    print("=" * 70)
    print("Copy these to your development.env file")
    print("=" * 70)
