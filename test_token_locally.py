#!/usr/bin/env python
"""
Test para verificar que el token existe en la BD
Ejecutar: python test_token_locally.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'takahe.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from api.models import Token

# El token del error
token_str = "3d4ZdATCE8BZHXdPqZKXq7FPCYeKt7r4kZzy-JTRkVy7ciNb46vKmDzowg"

print("Buscando token en la base de datos...")
print(f"Token: {token_str[:30]}...")
print()

try:
    token = Token.objects.select_related("identity").get(
        token=token_str,
        revoked__isnull=True,
    )
    print("✓ TOKEN ENCONTRADO!")
    print(f"  Identity: {token.identity.handle}")
    print(f"  Identity ID: {token.identity.id}")
    print(f"  User: {token.user}")
    print(f"  Scopes: {token.scopes}")
    print(f"  Created: {token.created}")
    print(f"  Revoked: {token.revoked}")
    print()
    print("El token ES VÁLIDO. El problema está en otro lado.")
except Token.DoesNotExist:
    print("✗ TOKEN NO ENCONTRADO")
    print()
    print("Posibilidades:")
    print("1. El token fue revocado")
    print("2. El token no existe en esta base de datos")
    print("3. Estás usando una BD diferente en producción")
    print()
    
    # Buscar tokens similares
    print("Buscando tokens similares...")
    similar = Token.objects.filter(token__startswith=token_str[:20])
    if similar.exists():
        print(f"Encontrados {similar.count()} tokens que empiezan similar:")
        for t in similar[:5]:
            print(f"  - {t.token[:50]}... (revoked: {t.revoked is not None})")
    else:
        print("No se encontraron tokens similares")
        
    print()
    print("Total de tokens activos:", Token.objects.filter(revoked__isnull=True).count())
except Exception as e:
    print(f"✗ ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

