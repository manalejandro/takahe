#!/usr/bin/env python3
"""
Script de prueba para verificar la funcionalidad de push subscriptions en Takahe.

Este script ayuda a diagnosticar problemas con las suscripciones push.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "takahe.settings")
django.setup()

from django.conf import settings
from api.models import Token, Application
from users.models import Identity, User


def check_vapid_configuration():
    """Verificar que las claves VAPID estén configuradas."""
    print("=" * 70)
    print("1. Verificando configuración VAPID...")
    print("=" * 70)
    
    has_public = bool(settings.SETUP.VAPID_PUBLIC_KEY)
    has_private = bool(settings.SETUP.VAPID_PRIVATE_KEY)
    
    print(f"VAPID_PUBLIC_KEY configurado: {has_public}")
    if has_public:
        print(f"  Clave pública: {settings.SETUP.VAPID_PUBLIC_KEY[:20]}...")
    
    print(f"VAPID_PRIVATE_KEY configurado: {has_private}")
    if has_private:
        print(f"  Clave privada: {settings.SETUP.VAPID_PRIVATE_KEY[:20]}...")
    
    if not (has_public and has_private):
        print("\n⚠️  ADVERTENCIA: Las claves VAPID no están configuradas!")
        print("Ejecuta: python scripts/generate_vapid_keys.py")
        return False
    
    print("\n✅ Claves VAPID configuradas correctamente\n")
    return True


def check_tokens_with_push():
    """Verificar tokens con suscripciones push."""
    print("=" * 70)
    print("2. Verificando tokens con suscripciones push...")
    print("=" * 70)
    
    tokens = Token.objects.filter(push_subscription__isnull=False, revoked__isnull=True)
    count = tokens.count()
    
    print(f"Tokens activos con push_subscription: {count}")
    
    if count == 0:
        print("\n⚠️  No hay tokens con suscripciones push activas")
        print("Esto es normal si aún no has configurado push en Elk\n")
        return
    
    print("\nDetalles de tokens con push:")
    for token in tokens[:5]:  # Mostrar máximo 5
        print(f"\n  Token ID: {token.id}")
        print(f"  Identity: {token.identity.handle if token.identity else 'N/A'}")
        print(f"  Scopes: {', '.join(token.scopes)}")
        
        if token.push_subscription:
            sub = token.push_subscription
            print(f"  Endpoint: {sub.get('endpoint', 'N/A')[:50]}...")
            print(f"  Policy: {sub.get('policy', 'N/A')}")
            
            alerts = sub.get('alerts', {})
            enabled_alerts = [k for k, v in alerts.items() if v]
            print(f"  Alertas habilitadas: {', '.join(enabled_alerts) if enabled_alerts else 'ninguna'}")
            
            keys = sub.get('keys', {})
            has_keys = 'p256dh' in keys and 'auth' in keys
            print(f"  Keys presentes: {'✅ Sí' if has_keys else '❌ No'}")
    
    print(f"\n✅ {count} token(s) con suscripciones push\n")


def test_push_subscription_schema():
    """Probar el esquema de push subscription."""
    print("=" * 70)
    print("3. Probando el esquema PushSubscriptionSchema...")
    print("=" * 70)
    
    from api.models.token import PushSubscriptionSchema
    
    test_data = {
        "endpoint": "https://example.com/push/endpoint",
        "keys": {
            "p256dh": "test_p256dh_key",
            "auth": "test_auth_key"
        },
        "alerts": {
            "mention": True,
            "follow": True,
            "favourite": False,
            "reblog": False,
            "poll": False
        },
        "policy": "all"
    }
    
    try:
        schema = PushSubscriptionSchema(**test_data)
        print("✅ Esquema de validación funciona correctamente")
        print(f"   Endpoint: {schema.endpoint}")
        print(f"   Policy: {schema.policy}")
        print(f"   Keys: p256dh y auth presentes")
        
        # Verificar que se puede convertir a dict
        dict_data = schema.dict()
        print("✅ Conversión a dict funciona correctamente\n")
        return True
        
    except Exception as e:
        print(f"❌ Error al validar el esquema: {e}\n")
        return False


def check_api_endpoints():
    """Verificar que los endpoints de API estén disponibles."""
    print("=" * 70)
    print("4. Verificando endpoints de API...")
    print("=" * 70)
    
    try:
        from api.views import push
        print("✅ Módulo api.views.push importado correctamente")
        print("   Endpoints disponibles:")
        print("   - POST /api/v1/push/subscription (create_subscription)")
        print("   - GET  /api/v1/push/subscription (get_subscription)")
        print("   - PUT  /api/v1/push/subscription (update_subscription)")
        print("   - DELETE /api/v1/push/subscription (delete_subscription)")
        print()
        return True
    except Exception as e:
        print(f"❌ Error al importar api.views.push: {e}\n")
        return False


def check_push_notification_service():
    """Verificar que el servicio de notificaciones push esté disponible."""
    print("=" * 70)
    print("5. Verificando servicio de notificaciones push...")
    print("=" * 70)
    
    try:
        from activities.services.push_notifications import PushNotificationSender
        print("✅ Servicio PushNotificationSender importado correctamente")
        
        try:
            import pywebpush
            print("✅ Librería pywebpush instalada")
        except ImportError:
            print("❌ Librería pywebpush NO instalada")
            print("   Ejecuta: pip install pywebpush")
            return False
        
        try:
            from py_vapid import Vapid
            print("✅ Librería py-vapid instalada")
        except ImportError:
            print("❌ Librería py-vapid NO instalada")
            print("   Ejecuta: pip install py-vapid")
            return False
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ Error al importar PushNotificationSender: {e}")
        print("   Verifica que el archivo activities/services/push_notifications.py exista\n")
        return False


def main():
    """Ejecutar todas las verificaciones."""
    print("\n" + "=" * 70)
    print("DIAGNÓSTICO DE PUSH NOTIFICATIONS EN TAKAHE")
    print("=" * 70 + "\n")
    
    results = []
    
    # Ejecutar verificaciones
    results.append(("VAPID configurado", check_vapid_configuration()))
    results.append(("Tokens con push", check_tokens_with_push() is not False))
    results.append(("Schema válido", test_push_subscription_schema()))
    results.append(("API endpoints", check_api_endpoints()))
    results.append(("Servicio push", check_push_notification_service()))
    
    # Resumen
    print("=" * 70)
    print("RESUMEN")
    print("=" * 70)
    
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {name}")
    
    all_passed = all(r[1] for r in results)
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ Todas las verificaciones pasaron correctamente!")
        print("=" * 70)
        print("\nPróximos pasos:")
        print("1. Conéctate a Elk desde tu navegador")
        print("2. Ve a Configuración → Notificaciones")
        print("3. Habilita las notificaciones push")
        print("4. Prueba recibir una notificación")
    else:
        print("⚠️  Algunas verificaciones fallaron")
        print("=" * 70)
        print("\nRevisa los errores arriba y corrige los problemas.")
        print("Consulta PUSH_NOTIFICATIONS_SETUP.md para más información.")
    print()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
