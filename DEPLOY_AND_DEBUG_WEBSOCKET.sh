#!/bin/bash
# Script para desplegar y debuggear el WebSocket en producción
# Ejecutar en el servidor: social.manalejandro.com

echo "==================================================="
echo "  DEPLOY Y DEBUG DE WEBSOCKET - PRODUCCIÓN"
echo "==================================================="
echo ""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}📋 PASO 1: Verificar el commit actual${NC}"
echo "Commit actual:"
git log -1 --oneline
echo ""
echo "Debe ser: 5a5462a CRITICAL FIX: Accept WebSocket BEFORE validation..."
read -p "¿Es el commit correcto? (presiona Enter para continuar)"

echo ""
echo -e "${YELLOW}📦 PASO 2: Rebuild del container${NC}"
echo "Esto puede tardar varios minutos..."
docker compose down
docker compose build --no-cache web
docker compose up -d

echo ""
echo -e "${YELLOW}⏱️  Esperando 10 segundos a que el servidor inicie...${NC}"
sleep 10

echo ""
echo -e "${YELLOW}🔍 PASO 3: Verificar que el servidor está corriendo${NC}"
docker compose ps

echo ""
echo -e "${YELLOW}🔐 PASO 4: Verificar que el token existe${NC}"
echo "Ejecutando test del token..."
docker compose exec -T web python /app/test_token_locally.py

echo ""
echo -e "${GREEN}✓ Container rebuilt y token verificado${NC}"
echo ""
echo -e "${YELLOW}======================================${NC}"
echo -e "${YELLOW}AHORA ABRE OTRA TERMINAL Y EJECUTA:${NC}"
echo -e "${YELLOW}docker compose logs -f web${NC}"
echo -e "${YELLOW}======================================${NC}"
echo ""
echo "Luego, desde tu navegador, conecta al WebSocket:"
echo "wss://social.manalejandro.com/api/v1/streaming?stream=user&access_token=TU_TOKEN"
echo ""
echo "En los logs deberías ver:"
echo "  [ASGI Router] Request type: websocket, path: /api/v1/streaming"
echo "  [ASGI Router] Routing to WebSocket handler"
echo "  Attempting to authenticate with token: ..."
echo "  ✓ Token found: ..."
echo "  ✓ Authenticated as: ..."
echo ""
echo -e "${GREEN}Si ves esos mensajes, el WebSocket está funcionando!${NC}"
