#!/bin/bash
# Script para debuggear WebSocket authentication
# Ejecutar en el servidor de producción

echo "======================================"
echo "Debugging WebSocket Authentication"
echo "======================================"
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}Este script te ayudará a debuggear el problema de autenticación del WebSocket${NC}"
echo ""

echo "1. Pull de los últimos cambios"
echo "   git pull origin feature/improve_security"
echo ""

echo "2. Rebuild del container"
echo "   docker compose down"
echo "   docker compose build --no-cache"
echo "   docker compose up -d"
echo ""

echo "3. Ver logs en tiempo real (en otra terminal)"
echo "   docker compose logs -f web"
echo ""

echo "4. Probar conexión WebSocket"
echo "   Intenta conectar desde el navegador"
echo ""

echo "5. Buscar en los logs:"
echo "   - 'Token found:' (debería aparecer si el token es válido)"
echo "   - 'Token not found:' (aparece si el token no existe)"
echo "   - 'Authenticated as identity:' (muestra quién se autenticó)"
echo "   - 'WebSocket auth failed:' (error de autenticación)"
echo "   - 'Token validation error:' (otro tipo de error)"
echo ""

echo -e "${YELLOW}Comandos útiles:${NC}"
echo ""
echo "Ver últimos logs:"
echo "  docker compose logs --tail=100 web"
echo ""
echo "Buscar errores:"
echo "  docker compose logs web | grep -i error"
echo ""
echo "Buscar mensajes de token:"
echo "  docker compose logs web | grep -i token"
echo ""
echo "Entrar al container:"
echo "  docker compose exec web bash"
echo ""
echo "Verificar tokens en la BD (dentro del container):"
echo "  python manage.py shell"
echo "  >>> from api.models import Token"
echo "  >>> Token.objects.filter(revoked__isnull=True).count()"
echo "  >>> Token.objects.filter(token__startswith='Jy8e').first()"
echo ""

echo -e "${YELLOW}Verificar token específico:${NC}"
echo "TOKEN='Jy8e0NViwcw9T4jZRrPq0BZlZfkU9hgVnKVWrAgtuhQA3MTDGWWNU2fwVA'"
echo ""
echo "docker compose exec web python manage.py shell << EOF"
echo "from api.models import Token"
echo "try:"
echo "    token = Token.objects.select_related('identity').get(token='\$TOKEN', revoked__isnull=True)"
echo "    print(f'Token válido para: {token.identity.handle}')"
echo "    print(f'Scopes: {token.scopes}')"
echo "except Token.DoesNotExist:"
echo "    print('Token no encontrado o revocado')"
echo "EOF"
echo ""

echo -e "${GREEN}Después de ver los logs, podrás identificar el problema exacto${NC}"
