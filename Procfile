# Web server with WebSocket support (ASGI with uvicorn)
web: uvicorn takahe.asgi:application --host 0.0.0.0 --port ${PORT:-8000} --workers 4

# Alternative: Traditional WSGI server (no WebSocket support)
# web: gunicorn takahe.wsgi:application --workers 8

worker: python manage.py runstator
release: python manage.py migrate
