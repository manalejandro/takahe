# Despliegue con soporte de WebSocket

## Configuración del servidor

Para soportar la API de streaming con WebSocket, el servidor debe usar ASGI en lugar de WSGI.

### Opción 1: Uvicorn (Recomendado)

Uvicorn es un servidor ASGI rápido que soporta WebSockets nativamente.

```bash
# Desarrollo
uvicorn takahe.asgi:application --reload --host 0.0.0.0 --port 8000

# Producción
uvicorn takahe.asgi:application --host 0.0.0.0 --port 8000 --workers 4
```

### Opción 2: Gunicorn + Uvicorn Workers

Puedes usar Gunicorn con workers de Uvicorn para mejor gestión de procesos:

```bash
gunicorn takahe.asgi:application -k uvicorn.workers.UvicornWorker --workers 4 --bind 0.0.0.0:8000
```

### Opción 3: Daphne

Daphne es otro servidor ASGI que soporta WebSockets:

```bash
daphne -b 0.0.0.0 -p 8000 takahe.asgi:application
```

## Configuración de Nginx

Para WebSocket es necesario configurar Nginx correctamente para manejar las actualizaciones de protocolo.

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    # Configuración SSL...
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Configuración especial para WebSocket
    location /api/v1/streaming {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts largos para conexiones persistentes
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }
}
```

## Docker

Si usas Docker, asegúrate de que tu Dockerfile use uvicorn:

```dockerfile
# Dockerfile
FROM python:3.11

WORKDIR /takahe

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Usar uvicorn en lugar de gunicorn
CMD ["uvicorn", "takahe.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

## Docker Compose

Ejemplo de configuración con docker-compose:

```yaml
version: '3.8'

services:
  web:
    build: .
    command: uvicorn takahe.asgi:application --host 0.0.0.0 --port 8000 --workers 4
    ports:
      - "8000:8000"
    environment:
      - DATABASE_SERVER=postgresql://user:pass@db:5432/takahe
      - TAKAHE_MAIN_DOMAIN=yourdomain.com
    depends_on:
      - db
  
  stator:
    build: .
    command: python manage.py runstator
    environment:
      - DATABASE_SERVER=postgresql://user:pass@db:5432/takahe
    depends_on:
      - db
  
  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=takahe
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass

volumes:
  postgres_data:
```

## Verificación

Para verificar que WebSocket funciona correctamente:

```bash
# Instalar websockets
pip install websockets

# Probar la conexión
python test_websocket_streaming.py public

# Con tu dominio
TAKAHE_URL=wss://yourdomain.com python test_websocket_streaming.py public
```

## Compatibilidad hacia atrás

Si no puedes usar ASGI/WebSocket, la API de streaming también soporta Server-Sent Events (SSE) sobre HTTP/HTTPS normal, que funciona con servidores WSGI tradicionales como Gunicorn:

```bash
# Usar Gunicorn (solo SSE, sin WebSocket)
gunicorn takahe.wsgi:application --workers 8
```

Los clientes podrán usar SSE en lugar de WebSocket automáticamente.

## Problemas comunes

### WebSocket connection refused

- **Causa**: El servidor está usando Gunicorn con WSGI
- **Solución**: Cambiar a Uvicorn o Daphne (ASGI)

### 502 Bad Gateway con Nginx

- **Causa**: Nginx no está configurado para WebSocket
- **Solución**: Agregar las configuraciones de `Upgrade` y `Connection` en la configuración de Nginx

### Connection timeout

- **Causa**: Timeouts demasiado cortos en el proxy
- **Solución**: Aumentar `proxy_read_timeout` y `proxy_send_timeout` en Nginx

## Referencias

- [Django ASGI documentation](https://docs.djangoproject.com/en/stable/howto/deployment/asgi/)
- [Uvicorn deployment](https://www.uvicorn.org/deployment/)
- [WebSocket RFC](https://datatracker.ietf.org/doc/html/rfc6455)
