# API de Streaming

## Descripción

El endpoint `/api/v1/streaming` proporciona acceso en tiempo real a las actualizaciones de la línea de tiempo. Es compatible con la API de Mastodon y soporta dos protocolos:

1. **WebSocket (wss://)** - Conexión bidireccional en tiempo real
2. **Server-Sent Events (SSE)** - Conexión unidireccional sobre HTTP/HTTPS

## Endpoints

### WebSocket: wss://[domain]/api/v1/streaming

Conexión WebSocket para streaming en tiempo real.

**Parámetros de consulta:**

- `stream` (requerido): Tipo de stream a seguir
  - `user`: Eventos de la línea de tiempo del usuario autenticado (requiere autenticación)
  - `public`: Línea de tiempo pública federada
  - `public:local`: Línea de tiempo pública local
  - `hashtag`: Actualizaciones de un hashtag específico (requiere parámetro `tag`)
  - `hashtag:local`: Actualizaciones de un hashtag local (requiere parámetro `tag`)
  - `list`: Actualizaciones de una lista específica (requiere parámetro `list`)

- `tag` (opcional): Hashtag a seguir (requerido para streams de tipo `hashtag` y `hashtag:local`)
- `list` (opcional): ID de lista a seguir (requerido para streams de tipo `list`)
- `access_token` (opcional): Token de acceso para autenticación (requerido para stream de tipo `user`)

**Formato de mensajes:**

Los mensajes WebSocket se envían como JSON con la siguiente estructura:

```json
{
  "event": "update",
  "payload": "{\"id\":\"123456\",\"content\":\"Hello world!\",\"account\":{...},\"created_at\":\"2026-01-28T10:00:00.000Z\"}"
}
```

**Tipos de eventos:**

- `update`: Nuevo post en la línea de tiempo
- `notification`: Nueva notificación (solo en stream `user`)
- `delete`: Post eliminado
- `filters_changed`: Filtros actualizados (solo en stream `user`)

### HTTP: GET /api/v1/streaming

Abre una conexión de streaming para recibir actualizaciones en tiempo real.

**Parámetros de consulta:**

- `stream` (requerido): Tipo de stream a seguir
  - `user`: Eventos de la línea de tiempo del usuario autenticado (requiere autenticación)
  - `public`: Línea de tiempo pública federada
  - `public:local`: Línea de tiempo pública local
  - `hashtag`: Actualizaciones de un hashtag específico (requiere parámetro `tag`)
  - `hashtag:local`: Actualizaciones de un hashtag local (requiere parámetro `tag`)
  - `list`: Actualizaciones de una lista específica (requiere parámetro `list`)

- `tag` (opcional): Hashtag a seguir (requerido para streams de tipo `hashtag` y `hashtag:local`)
- `list` (opcional): ID de lista a seguir (requerido para streams de tipo `list`)

**Headers:**

- `Authorization: Bearer <token>` (requerido para stream de tipo `user`)

**Respuesta:**

- Content-Type: `text/event-stream`
- Formato: Server-Sent Events (SSE)

**Tipos de eventos:**

- `update`: Nuevo post en la línea de tiempo
- `ping`: Keepalive para mantener la conexión abierta
- `error`: Error durante el streaming

**Ejemplo de evento:**

```
event: update
data: {"id":"123456","content":"Hello world!","account":{...},"created_at":"2026-01-28T10:00:00.000Z"}

```

### GET /api/v1/streaming/health

Endpoint de verificación de salud del servicio de streaming.

**Respuesta:**

```json
{
  "status": "ok"
}
```

## Ejemplos de uso

### WebSocket con JavaScript

```javascript
// Conectar al stream público
const ws = new WebSocket('wss://yourdomain.com/api/v1/streaming?stream=public');

ws.onopen = () => {
  console.log('WebSocket connected');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.event);
  
  if (data.event === 'update') {
    const status = JSON.parse(data.payload);
    console.log('New post:', status);
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('WebSocket disconnected');
};

// Stream de usuario con token
const wsUser = new WebSocket(
  'wss://yourdomain.com/api/v1/streaming?stream=user&access_token=YOUR_TOKEN'
);
```

### WebSocket con Python (websockets library)

```python
import asyncio
import websockets
import json

async def stream_public():
    uri = "wss://yourdomain.com/api/v1/streaming?stream=public"
    
    async with websockets.connect(uri) as websocket:
        print("Connected to stream")
        
        async for message in websocket:
            data = json.loads(message)
            
            if data['event'] == 'update':
                status = json.loads(data['payload'])
                print(f"New post: {status['content']}")

asyncio.run(stream_public())
```

### Server-Sent Events (SSE)

### Con curl

```bash
# Stream público
curl -N "http://localhost:8000/api/v1/streaming?stream=public"

# Stream de hashtag
curl -N "http://localhost:8000/api/v1/streaming?stream=hashtag&tag=takahe"

# Stream de usuario (con token)
curl -N -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/streaming?stream=user"
```

### Con el script de prueba incluido

```bash
# Stream público
python test_streaming_api.py public

# Stream de hashtag
python test_streaming_api.py hashtag takahe

# Stream de usuario con token
python test_streaming_api.py user "" YOUR_TOKEN
```

### Con JavaScript (EventSource)

```javascript
// Stream público
const eventSource = new EventSource('http://localhost:8000/api/v1/streaming?stream=public');

eventSource.addEventListener('update', (event) => {
  const status = JSON.parse(event.data);
  console.log('New post:', status);
});

eventSource.addEventListener('ping', (event) => {
  console.log('Keepalive ping received');
});

eventSource.onerror = (error) => {
  console.error('Streaming error:', error);
  eventSource.close();
};
```

### Con Python requests

```python
import requests
import json

url = "http://localhost:8000/api/v1/streaming"
params = {"stream": "public"}

response = requests.get(url, params=params, stream=True)

for line in response.iter_lines(decode_unicode=True):
    if line.startswith('data: '):
        data = json.loads(line[6:])  # Skip "data: "
        print(f"New post: {data['content']}")
```

## Notas de implementación

- **Protocolo dual**: El mismo endpoint soporta tanto WebSocket como SSE
- **WebSocket**: Conexión bidireccional, más eficiente para aplicaciones web modernas
- **SSE**: Conexión unidireccional, más simple, funciona con HTTP/1.1
- Las conexiones se mantienen abiertas indefinidamente hasta que el cliente se desconecta
- Para SSE: Se envían eventos ping cada 15 segundos para mantener la conexión viva
- Para WebSocket: No se requieren pings explícitos, el protocolo maneja keepalive
- El servidor verifica nuevas actualizaciones cada 2 segundos
- Compatible con despliegues ASGI (uvicorn, daphne, hypercorn)
- **IMPORTANTE**: Para WebSocket se requiere un servidor ASGI (uvicorn está incluido en requirements.txt)
- Las líneas de tiempo públicas pueden estar deshabilitadas según la configuración del servidor

## Compatibilidad

Este endpoint es compatible con la API de Mastodon, por lo que los clientes de Mastodon pueden usarlo sin modificaciones.

## Limitaciones actuales

- El stream de tipo `list` aún no está completamente implementado
- No se incluyen eventos de notificación en el stream de usuario (próximamente)
- El filtrado avanzado no está implementado

## Seguridad

- Los streams públicos no requieren autenticación, pero pueden estar deshabilitados por el administrador
- El stream de usuario requiere un token de acceso válido con scope `read:statuses`
- Las conexiones se validan contra la configuración CORS del servidor
