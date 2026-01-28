#!/bin/bash
# Script para desplegar soporte de WebSocket en producción
# Uso: bash DEPLOY_WEBSOCKET.sh

set -e

echo "======================================"
echo "Despliegue de WebSocket Streaming"
echo "======================================"
echo ""

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}1. Verificando cambios locales...${NC}"
if ! git diff-index --quiet HEAD --; then
    echo -e "${RED}Hay cambios sin commitear. Commitea primero.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Todo está commiteado${NC}"
echo ""

echo -e "${YELLOW}2. Verificando branch actual...${NC}"
CURRENT_BRANCH=$(git branch --show-current)
echo "Branch actual: $CURRENT_BRANCH"
echo ""

echo -e "${YELLOW}3. ¿Deseas continuar con el despliegue? [y/N]${NC}"
read -r response
if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "Despliegue cancelado"
    exit 0
fi
echo ""

echo -e "${YELLOW}4. Mostrando archivos modificados en el último commit...${NC}"
git show --name-only --oneline HEAD
echo ""

echo -e "${YELLOW}5. Push a origin...${NC}"
git push origin "$CURRENT_BRANCH"
echo -e "${GREEN}✓ Push completado${NC}"
echo ""

echo "======================================"
echo "Ahora en tu servidor de producción:"
echo "======================================"
echo ""
echo "Ejecuta estos comandos en social.manalejandro.com:"
echo ""
echo "  cd /ruta/a/takahe"
echo "  git pull origin $CURRENT_BRANCH"
echo "  docker compose down"
echo "  docker compose build --no-cache"
echo "  docker compose up -d"
echo ""
echo "O si usas docker-compose (version antigua):"
echo ""
echo "  cd /ruta/a/takahe"
echo "  git pull origin $CURRENT_BRANCH"
echo "  docker-compose down"
echo "  docker-compose build --no-cache"
echo "  docker-compose up -d"
echo ""
echo "======================================"
echo "Verificación:"
echo "======================================"
echo ""
echo "1. Verificar logs:"
echo "   docker compose logs -f web"
echo ""
echo "2. Buscar en logs:"
echo "   - 'uvicorn' (debe aparecer, no 'gunicorn')"
echo "   - 'Application startup complete'"
echo ""
echo "3. Probar WebSocket:"
echo "   python test_websocket_streaming.py user TU_TOKEN"
echo ""
echo -e "${GREEN}Script de despliegue completado${NC}"
