#!/bin/bash
set -e

echo "======================================================================"
echo "  Setup de Notificaciones Push para Takahe + Elk"
echo "======================================================================"
echo ""

cd "$(dirname "$0")"

# Step 1: Check if virtualenv exists and recreate if needed
echo "[1/6] Verificando virtualenv..."
if [ ! -f ".venv/bin/python" ]; then
    echo "  → Creando virtualenv..."
    rm -rf .venv
    python3 -m venv .venv
else
    echo "  ✓ Virtualenv existe"
fi

# Activate virtualenv
source .venv/bin/activate

# Step 2: Install dependencies
echo ""
echo "[2/6] Instalando dependencias Python..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "  ✓ Dependencias instaladas"

# Step 3: Generate VAPID keys if not already configured
echo ""
echo "[3/6] Verificando claves VAPID..."
if grep -q "^TAKAHE_VAPID_PUBLIC_KEY=" development.env 2>/dev/null; then
    echo "  ✓ Claves VAPID ya configuradas"
else
    echo "  → Generando nuevas claves VAPID..."
    
    # Generate keys
    KEYS_OUTPUT=$(python scripts/generate_vapid_keys.py)
    
    # Extract keys
    PUBLIC_KEY=$(echo "$KEYS_OUTPUT" | grep "Public Key:" | cut -d' ' -f4-)
    PRIVATE_KEY=$(echo "$KEYS_OUTPUT" | grep "Private Key:" | cut -d' ' -f4-)
    
    if [ -z "$PUBLIC_KEY" ] || [ -z "$PRIVATE_KEY" ]; then
        echo "  ✗ Error generando claves VAPID"
        exit 1
    fi
    
    # Add to development.env
    echo "" >> development.env
    echo "# VAPID Keys (generated $(date))" >> development.env
    echo "TAKAHE_VAPID_PUBLIC_KEY=\"$PUBLIC_KEY\"" >> development.env
    echo "TAKAHE_VAPID_PRIVATE_KEY=\"$PRIVATE_KEY\"" >> development.env
    
    echo "  ✓ Claves VAPID generadas y guardadas en development.env"
    echo ""
    echo "  Public Key:  $PUBLIC_KEY"
    echo "  Private Key: ${PRIVATE_KEY:0:20}..."
fi

# Step 4: Run migrations
echo ""
echo "[4/6] Ejecutando migraciones..."
python manage.py migrate --noinput
echo "  ✓ Migraciones completadas"

# Step 5: Verify instance endpoint
echo ""
echo "[5/6] Verificando configuración..."
echo "  → Iniciando servidor temporal para prueba..."

# Start server in background
python manage.py runserver 0.0.0.0:8000 > /tmp/takahe_test.log 2>&1 &
SERVER_PID=$!

# Wait for server to start
sleep 3

# Test endpoint
if curl -s http://localhost:8000/api/v2/instance | grep -q "vapid"; then
    echo "  ✓ Endpoint /api/v2/instance responde correctamente"
    
    # Show vapid key
    VAPID_FROM_API=$(curl -s http://localhost:8000/api/v2/instance | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('configuration', {}).get('vapid', {}).get('public_key', 'NOT FOUND'))")
    
    if [ "$VAPID_FROM_API" != "NOT FOUND" ] && [ ! -z "$VAPID_FROM_API" ]; then
        echo "  ✓ VAPID key disponible en API: ${VAPID_FROM_API:0:30}..."
    else
        echo "  ⚠ VAPID key no encontrada en respuesta de API"
        echo "  → Asegúrate de reiniciar el servidor después de este script"
    fi
else
    echo "  ⚠ No se pudo verificar endpoint (esto es normal si el servidor ya estaba corriendo)"
fi

# Stop test server
kill $SERVER_PID 2>/dev/null || true
sleep 1

echo ""
echo "[6/6] Setup completado"
echo ""
echo "======================================================================"
echo "  Próximos pasos:"
echo "======================================================================"
echo ""
echo "1. Inicia el servidor Takahe:"
echo "   cd /home/ale/projects/activitypub/takahe"
echo "   source .venv/bin/activate"
echo "   python manage.py runserver 0.0.0.0:8000"
echo ""
echo "2. Desde Elk:"
echo "   - Cierra sesión si ya estabas logueado"
echo "   - Vuelve a iniciar sesión (esto refrescará el vapidKey)"
echo "   - Ve a Settings → Notifications → Push Notifications"
echo "   - Haz clic en 'Habilitar notificaciones push'"
echo ""
echo "3. Verifica los logs del servidor para ver la creación del push subscription"
echo ""
echo "======================================================================"
