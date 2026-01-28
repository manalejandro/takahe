# Fix: WebSocket 401 Error - Accept Before Validation

## 🐛 El Problema

El WebSocket estaba devolviendo `401 Unauthorized` con headers HTTP normales (`Content-Type: application/json`), lo que indica que **la conexión nunca se establecía como WebSocket**.

### Síntomas
```
GET wss://social.manalejandro.com/api/v1/streaming?stream=user&access_token=...
Status: 401 Unauthorized
Content-Type: application/json
Content-Length: 52
```

Estos headers HTTP normales indican que:
- El WebSocket nunca fue aceptado
- Django/middleware procesó la petición como HTTP normal
- El código de validación nunca se ejecutó

## 🔍 Causa Raíz

En el protocolo WebSocket, **DEBES aceptar la conexión ANTES de hacer cualquier validación**:

```python
# ❌ INCORRECTO - Valida antes de aceptar
async def streaming_websocket(scope, receive, send):
    # Parse query string
    params = parse_qs(...)
    
    # Validate stream parameter
    if not stream:
        await send({"type": "websocket.close", ...})  # NUNCA LLEGA AQUÍ
        return
```

El problema es que **si no aceptas primero**, el servidor ASGI/Django trata la petición como HTTP normal y aplica middleware HTTP, que puede rechazarla con 401 antes de que llegue a tu código.

## ✅ La Solución

**Aceptar la conexión WebSocket PRIMERO**, luego validar:

```python
# ✅ CORRECTO - Acepta primero, valida después
async def streaming_websocket(scope, receive, send):
    # CRITICAL: Accept WebSocket FIRST before any validation
    await send({
        "type": "websocket.accept",
    })
    
    # Ahora sí, parsear y validar
    query_string = scope.get("query_string", b"").decode("utf-8")
    params = parse_qs(query_string)
    
    stream = params.get("stream", [None])[0]
    
    # Si hay error, cerrar el WebSocket (ya aceptado)
    if not stream:
        await send({
            "type": "websocket.close",
            "code": 4400,
            "reason": "stream parameter is required",
        })
        return
```

## 📝 Cambios Realizados

### 1. `api/websocket_streaming.py`
- Agregado `websocket.accept` al inicio de `streaming_websocket()`
- Ahora valida DESPUÉS de aceptar la conexión

### 2. `takahe/asgi.py`
- Agregado logging para debug:
  ```python
  print(f"[ASGI Router] Request type: {scope['type']}, path: {scope.get('path', 'N/A')}")
  ```

## 🧪 Cómo Verificar

1. **Desplegar en producción:**
   ```bash
   cd /ruta/a/takahe
   git pull origin feature/improve_security
   docker compose down
   docker compose build --no-cache web
   docker compose up -d
   ```

2. **Ver logs:**
   ```bash
   docker compose logs -f web
   ```

3. **Conectar desde navegador:**
   ```
   wss://social.manalejandro.com/api/v1/streaming?stream=user&access_token=TU_TOKEN
   ```

4. **Logs esperados:**
   ```
   [ASGI Router] Request type: websocket, path: /api/v1/streaming
   [ASGI Router] Routing to WebSocket handler
   Attempting to authenticate with token: X739ZBBcuCbLzCKp7Z...
   ✓ Token found: X739ZBBcuCbLzCKp7Z... for identity: usuario@...
   ✓ Authenticated as: usuario@... (ID: 123)
   ✓ All validations passed
   Starting event stream...
   ```

## 📚 Referencias

- [ASGI WebSocket Spec](https://asgi.readthedocs.io/en/latest/specs/www.html#websocket)
- [WebSocket Protocol RFC 6455](https://datatracker.ietf.org/doc/html/rfc6455)

## 🎓 Lección Aprendida

**En WebSockets, la secuencia SIEMPRE debe ser:**

1. ✅ Recibir conexión
2. ✅ **Aceptar conexión** (`websocket.accept`)
3. ✅ Validar autenticación
4. ✅ Enviar datos o cerrar con código de error

**NO** puedes validar antes de aceptar, porque la conexión nunca se establece como WebSocket y el servidor la trata como HTTP normal.
