#!/bin/bash
# Script para desplegar las notificaciones push en producción

echo "=== Desplegando notificaciones push en social.manalejandro.com ==="
echo ""

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}PASO 1: Hacer merge de feature/improve_security a main${NC}"
echo "Ejecuta estos comandos en tu máquina local:"
echo ""
echo "  cd /home/ale/projects/activitypub/takahe"
echo "  git checkout main"
echo "  git merge feature/improve_security"
echo "  git push origin main"
echo ""
echo "Presiona ENTER cuando hayas terminado..."
read

echo ""
echo -e "${YELLOW}PASO 2: En el servidor, ejecuta estos comandos:${NC}"
echo ""
cat << 'EOF'
# Ir al directorio de takahe
cd /ruta/donde/esta/takahe

# Actualizar código
git fetch
git checkout main
git pull origin main

# Verificar que las rutas push están presentes
echo "Verificando rutas push..."
grep -n "push/subscription" api/urls.py

# Verificar variables VAPID
echo ""
echo "Verificando variables VAPID..."
if grep -q "TAKAHE_VAPID_PUBLIC_KEY" .env; then
    echo "✓ VAPID keys encontradas"
else
    echo "✗ FALTAN las VAPID keys. Añádelas al archivo .env:"
    echo ""
    echo "TAKAHE_VAPID_PUBLIC_KEY=\"BKU1B_c_8DFPUXjgQNsNFi6MIrn5rzTh3d5CGo7NOpsIF-MY4qowgHU1Y_YAFAjNOTS5L9X2u8tBM3w4LxcEijU\""
    echo "TAKAHE_VAPID_PRIVATE_KEY=\"kwYCNps_Ix5nwSWQ-20yHD-Lzqdj0kvrVEwpQ2AAj5E\""
    echo ""
    echo "Presiona ENTER después de añadirlas..."
    read
fi

# Instalar/actualizar dependencias si es necesario
if ! pip show pywebpush > /dev/null 2>&1; then
    echo "Instalando pywebpush..."
    pip install pywebpush~=2.0.0 py-vapid~=1.9.1
fi

# Reiniciar el servidor
echo ""
echo "Reiniciando servidor Takahe..."
echo "Usa el comando apropiado para tu configuración:"
echo ""
echo "  systemctl restart takahe       # Si usas systemd"
echo "  supervisorctl restart takahe   # Si usas supervisor"
echo "  # O el método que uses para reiniciar"
echo ""
echo "Presiona ENTER después de reiniciar..."
read

# Probar la ruta
echo ""
echo "Probando la ruta push..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://social.manalejandro.com/api/v1/push/subscription)

if [ "$HTTP_CODE" == "401" ]; then
    echo "✓ ¡ÉXITO! La ruta responde 401 (necesita autenticación)"
    echo "Las notificaciones push están funcionando"
elif [ "$HTTP_CODE" == "404" ]; then
    echo "✗ ERROR: Todavía responde 404"
    echo "Revisa los logs del servidor:"
    echo "  journalctl -u takahe -n 50    # Si usas systemd"
    echo "  tail -f /var/log/takahe/*.log # Logs generales"
else
    echo "? Código inesperado: $HTTP_CODE"
fi

# Verificar endpoint VAPID
echo ""
echo "Verificando endpoint VAPID..."
curl -s https://social.manalejandro.com/api/v2/instance | grep -A2 vapid

echo ""
echo "=== Despliegue completado ==="
EOF

echo ""
echo -e "${GREEN}Guarda este script y ejecútalo en tu servidor${NC}"
