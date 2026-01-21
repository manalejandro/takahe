"""
VAPID Key utilities for converting between formats.

Web Push uses base64url encoding for public keys sent to browsers,
but pywebpush library expects PEM format for private keys.
"""
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ec import (
    EllipticCurvePrivateNumbers,
    EllipticCurvePublicNumbers,
    SECP256R1,
)
from cryptography.hazmat.backends import default_backend


def base64url_to_pem_private(base64url_key: str) -> str:
    """
    Convert base64url private key to PEM format.
    
    Args:
        base64url_key: Private key in base64url format (32 bytes)
    
    Returns:
        Private key in PEM format (PKCS8)
    """
    # Add padding if needed
    padding = '=' * (4 - len(base64url_key) % 4) if len(base64url_key) % 4 else ''
    private_bytes = base64.urlsafe_b64decode(base64url_key + padding)
    
    if len(private_bytes) != 32:
        raise ValueError(f"Private key must be 32 bytes, got {len(private_bytes)}")
    
    # Convert to integer
    private_int = int.from_bytes(private_bytes, byteorder='big')
    
    # We need to reconstruct the public key from private key
    # This requires using the elliptic curve math
    from cryptography.hazmat.primitives.asymmetric import ec
    private_key_obj = ec.derive_private_key(private_int, SECP256R1(), default_backend())
    
    # Convert to PEM
    private_pem = private_key_obj.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('ascii')
    
    return private_pem


def base64url_to_pem_public(base64url_key: str, private_base64url: str = None) -> str:
    """
    Convert base64url public key to PEM format.
    
    Args:
        base64url_key: Public key in base64url format (65 bytes uncompressed)
        private_base64url: Optional private key to derive public key from
    
    Returns:
        Public key in PEM format
    """
    # Add padding if needed
    padding = '=' * (4 - len(base64url_key) % 4) if len(base64url_key) % 4 else ''
    public_bytes = base64.urlsafe_b64decode(base64url_key + padding)
    
    if len(public_bytes) != 65:
        raise ValueError(f"Public key must be 65 bytes (uncompressed point), got {len(public_bytes)}")
    
    if public_bytes[0] != 0x04:
        raise ValueError("Public key must start with 0x04 (uncompressed point indicator)")
    
    # Extract x and y coordinates
    x_bytes = public_bytes[1:33]
    y_bytes = public_bytes[33:65]
    x = int.from_bytes(x_bytes, byteorder='big')
    y = int.from_bytes(y_bytes, byteorder='big')
    
    # Create public key
    public_numbers = EllipticCurvePublicNumbers(x, y, SECP256R1())
    public_key = public_numbers.public_key(default_backend())
    
    # Convert to PEM
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('ascii')
    
    return public_pem


def get_vapid_public_key_for_browser() -> str:
    """
    Get VAPID public key in format suitable for browsers (base64url).
    
    This reads from settings and returns the key as-is since we store
    it in base64url format.
    """
    from django.conf import settings
    return settings.SETUP.VAPID_PUBLIC_KEY


def get_vapid_private_key_for_pywebpush() -> str:
    """
    Get VAPID private key in format suitable for pywebpush (PEM).
    
    Converts from base64url storage format to PEM format.
    """
    from django.conf import settings
    base64url_key = settings.SETUP.VAPID_PRIVATE_KEY
    
    # Check if it's already PEM format
    if base64url_key and base64url_key.startswith('-----BEGIN'):
        return base64url_key
    
    # Convert from base64url to PEM
    return base64url_to_pem_private(base64url_key)


def get_vapid_public_key_pem() -> str:
    """
    Get VAPID public key in PEM format.
    
    Converts from base64url storage format to PEM format.
    """
    from django.conf import settings
    base64url_key = settings.SETUP.VAPID_PUBLIC_KEY
    
    # Check if it's already PEM format
    if base64url_key and base64url_key.startswith('-----BEGIN'):
        return base64url_key
    
    # Convert from base64url to PEM
    # For public key, we need the private key to derive it properly
    # Or we can use the raw base64url format
    return base64url_to_pem_public(base64url_key)
