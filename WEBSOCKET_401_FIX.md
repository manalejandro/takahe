# Fix: WebSocket 401 Error - Django Route Conflict

## 🐛 El Problema REAL

El WebSocket estaba devolviendo `401 Unauthorized` con headers HTTP normales (`Content-Type: application/json`), lo que indica que **la conexión nunca se establecía como WebSocket**.

### Síntomas
```
GET wss://social.manalejandro.com/api/v1/streaming?stream=user&access_token=...
Status: 401 Unauthorized
Content-Type: application/json
Content-Length: 52
```

Estos headers HTTP normales **NUNCA deberían aparecer en una conexión WebSocket**.

## 🔍 Causa Raíz - Django URL Route Conflict

### El Verdadero Problema

En `api/urls.py` existía una ruta HTTP que estaba **interceptando** todas las peticiones WebSocket:

```python
# api/urls.py
urlpatterns = [
    ...
    path("v1/streaming", streaming.streaming),  # ← BLOQUEABA WebSocket
    ...
]
```

### Flujo del Error (ANTES del fix)

```
1. Cliente → wss://server.com/api/v1/streaming?access_token=...
2. Uvicorn (ASGI) → Pasa petición a application()
3. Django ASGI App → Procesa TODAS las rutas HTTP primero
4. Django encuentra → path("v1/streaming", streaming.streaming)
5. Django aplica middleware HTTP → CORS, CSRF, Auth, etc.
6. Middleware Auth → No encuentra token en Authorization header
7. Django devuelve → 401 Unauthorized (HTTP response)
8. El código WebSocket en asgi.py → NUNCA SE EJECUTA
```

**El token estaba en query string (`?access_token=...`) pero Django middleware lo buscaba en headers HTTP (`Authorization: Bearer ...`)**.

## ✅ La Solución

### 1. Modificar `takahe/asgi.py` - Interceptar ANTES de Django

```python
async def application(scope, receive, send):
    path = scope.get("path", "")
    scope_type = scope["type"]
    
    # CRITICAL: Check streaming path BEFORE Django routing
    if path == "/api/v1/streaming":
        if scope_type == "websocket":
            # Direct WebSocket connection
            await streaming_websocket(scope, receive, send)
            return
        elif scope_type == "http":
            # Check for WebSocket Upgrade header
            headers_dict = dict(scope.get("headers", []))
            upgrade_header = headers_dict.get(b"upgrade", b"").lower()
            
            if upgrade_header == b"websocket":
                # Convert to WebSocket scope
                scope["type"] = "websocket"
                await streaming_websocket(scope, receive, send)
                return
    
    # Let Django handle everything else
    await django_asgi_app(scope, receive, send)
```

### 2. Eliminar Ruta Conflictiva en `api/urls.py`

```python
# BEFORE (WRONG):
path("v1/streaming", streaming.streaming),  # Conflicts with WebSocket

# AFTER (CORRECT):
# Removed - WebSocket handled by ASGI router in takahe/asgi.py
# Only keep health check:
path("v1/streaming/health", streaming.health),
```

## 📝 Flujo Correcto (DESPUÉS del fix)

```
1. Cliente → wss://server.com/api/v1/streaming?access_token=...
2. Uvicorn (ASGI) → Pasa petición a application()
3. ASGI Router → Detecta path="/api/v1/streaming" PRIMERO
4. ASGI Router → Redirige a streaming_websocket()
5. streaming_websocket() → Accept WebSocket connection
6. streaming_websocket() → Parse query string para access_token
7. streaming_websocket() → Valida token desde DB
8. streaming_websocket() → Inicia streaming de eventos
```

**Ahora NO pasa por Django middleware HTTP, por lo que el token en query string funciona correctamente.**

## 🧪 Cómo Verificar Localmente

```bash
# 1. Verificar que no hay rutas conflictivas
./verify_websocket_routing.sh

# 2. Buscar la ruta eliminada (NO debe aparecer)
grep -n 'path("v1/streaming".*streaming\.streaming' api/urls.py
# Output esperado: (ninguno)

# 3. Verificar ASGI intercepta el path
grep -A 5 'if path == "/api/v1/streaming"' takahe/asgi.py
# Debe mostrar el código de interceptación
```

## 🚀 Desplegar en Producción

```bash
# En tu servidor de producción:
cd /path/to/takahe

# Pull los cambios
git pull origin feature/improve_security

# Verificar que el fix está aplicado
git log --oneline -1
# Debe mostrar: "CRITICAL FIX: Remove HTTP route conflict..."

# Verificar routing
bash verify_websocket_routing.sh

# Reiniciar servicios
docker compose down
docker compose build --no-cache web
docker compose up -d

# Ver logs en tiempo real
docker compose logs -f web
```

## 📋 Logs Esperados

Cuando un cliente se conecta, deberías ver:

```
[ASGI Router] Request type: websocket, path: /api/v1/streaming
[ASGI Router] Routing to WebSocket handler
Attempting to authenticate with token: HVNczap2acmq...
✓ Token found: HVNczap2acmq... for identity: usuario@dominio
✓ Authenticated as: usuario@dominio (ID: 123)
✓ All validations passed, starting WebSocket streaming for: user
```

## 🐛 Si ANTES veías (INCORRECTO):

```
# Django logs mostrando 401:
"GET /api/v1/streaming HTTP/1.1" 401
```

**Esto significaba que Django HTTP estaba procesando la petición.**

## ✅ Ahora debes ver (CORRECTO):

```
[ASGI Router] Request type: websocket, path: /api/v1/streaming
[ASGI Router] Routing to WebSocket handler
```

**Sin logs de Django HTTP 401, porque no pasa por ahí.**

## 🎓 Lecciones Aprendidas

1. **Django URL routing tiene prioridad** sobre el routing personalizado en ASGI si no lo interceptas explícitamente.

2. **No puedes mezclar HTTP routes y WebSocket handlers** para el mismo path sin conflictos.

3. **El orden importa en ASGI**: Debes interceptar paths especiales ANTES de pasar a Django.

4. **Headers de respuesta revelan el problema**: `Content-Type: application/json` en una petición WebSocket = está siendo tratada como HTTP.

5. **Los tokens en query string** son válidos para WebSocket pero Django middleware HTTP los ignora (busca en `Authorization` header).

## 📚 Referencias

- [ASGI WebSocket Spec](https://asgi.readthedocs.io/en/latest/specs/www.html#websocket)
- [Django Channels Routing](https://channels.readthedocs.io/en/stable/topics/routing.html)
- [WebSocket Protocol RFC 6455](https://datatracker.ietf.org/doc/html/rfc6455)

