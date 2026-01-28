# Diagnóstico de Push Notifications

## Problema Reportado
Cuando haces clic en "Habilitar notificaciones push" en Elk, no pasa nada.

## Causa Raíz

### 1. Elk espera el VAPID key desde `/api/v2/instance`
El código de Elk busca la clave VAPID aquí:
```typescript
const v2InstanceVapidKey: string | undefined = v2Instance?.configuration?.vapid?.public_key
```

### 2. Takahe debe tener VAPID keys configuradas
En `takahe/development.env` o en variables de entorno del sistema.

### 3. Flujo completo:
1. Usuario hace clic en "Habilitar notificaciones push" en Elk
2. Elk verifica si `currentUser.value?.vapidKey` existe
3. Si NO existe, el botón se deshabilita (mensaje: "Re-authenticate required")
4. El vapidKey viene del endpoint `/api/v2/instance` en el campo `configuration.vapid.public_key`
5. Si existe, Elk usa ese key para suscribirse al servicio push

## Solución

### Paso 1: Generar las claves VAPID
```bash
cd /home/ale/projects/activitypub/takahe
python scripts/generate_vapid_keys.py
```

Esto generará algo como:
```
VAPID Keys Generated:
====================
Public Key:  BNp8Z3...
Private Key: vFQ2n9...

Add these to your environment:
TAKAHE_VAPID_PUBLIC_KEY="BNp8Z3..."
TAKAHE_VAPID_PRIVATE_KEY="vFQ2n9..."
```

### Paso 2: Configurar las variables de entorno

Opción A - En `development.env`:
```bash
TAKAHE_VAPID_PUBLIC_KEY="tu_clave_publica_aqui"
TAKAHE_VAPID_PRIVATE_KEY="tu_clave_privada_aqui"
```

Opción B - En el shell antes de ejecutar:
```bash
export TAKAHE_VAPID_PUBLIC_KEY="tu_clave_publica_aqui"
export TAKAHE_VAPID_PRIVATE_KEY="tu_clave_privada_aqui"
```

### Paso 3: Recrear el virtualenv e instalar dependencias
```bash
cd /home/ale/projects/activitypub/takahe
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Paso 4: Ejecutar migraciones
```bash
python manage.py migrate
```

### Paso 5: Iniciar el servidor
```bash
python manage.py runserver 0.0.0.0:8000
```

### Paso 6: Verificar que el VAPID key se devuelve
```bash
curl http://localhost:8000/api/v2/instance | jq '.configuration.vapid'
```

Deberías ver:
```json
{
  "public_key": "BNp8Z3..."
}
```

### Paso 7: Probar desde Elk
1. Cierra sesión en Elk si ya estabas logueado
2. Vuelve a iniciar sesión (esto refresca el vapidKey desde el servidor)
3. Ve a Settings → Notifications → Push Notifications
4. Click en "Habilitar notificaciones push"

## Verificación de errores

### Si el botón sigue deshabilitado:
- Abre la consola del navegador (F12)
- Ve a la tab "Application" → "Local Storage" → tu dominio de Elk
- Busca el key que contiene tu cuenta y verifica que tenga un `vapidKey`

### Si aparece error "invalid-vapid-key":
- Verifica que la clave pública sea válida base64url
- Regenera las claves con el script `generate_vapid_keys.py`

### Si el token se crea pero push_subscription queda null:
- Verifica los logs del servidor Takahe
- Deberías ver logs como:
  ```
  Creating push subscription for token XXX: endpoint=https://...
  Subscription data: {...}
  Push subscription saved successfully for token XXX
  ```

## Archivos Modificados

1. `takahe/api/views/instance.py` - Añadido vapid key a la respuesta
2. `takahe/api/views/push.py` - Corregida serialización de Hatchway Schema
3. `takahe/api/models/token.py` - Añadido logging para debugging
4. `takahe/api/schemas.py` - Corregido from_token() para no modificar original
5. `takahe/activities/services/push_notifications.py` - Nuevo servicio para enviar push
6. `takahe/activities/signals.py` - Auto-envío de notificaciones push
7. `takahe/activities/apps.py` - Carga de signals
8. `takahe/requirements.txt` - Añadidas dependencias pywebpush y py-vapid

## Estado Actual
- ✅ Código de Takahe listo
- ✅ Código de Elk ya soporta push notifications
- ❌ Falta: Generar claves VAPID
- ❌ Falta: Configurar variables de entorno
- ❌ Falta: Instalar dependencias Python
- ❌ Falta: Reiniciar servidor Takahe
