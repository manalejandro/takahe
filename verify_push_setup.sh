#!/bin/bash
set -e

echo "=========================================================================="
echo "  Verificación de Push Notifications: Elk + Takahe"
echo "=========================================================================="
echo ""

cd "$(dirname "$0")"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check 1: VAPID keys configured
echo "[1/5] Verificando claves VAPID en development.env..."
if grep -q "^TAKAHE_VAPID_PUBLIC_KEY=" development.env && grep -q "^TAKAHE_VAPID_PRIVATE_KEY=" development.env; then
    PUBLIC_KEY=$(grep "^TAKAHE_VAPID_PUBLIC_KEY=" development.env | cut -d'"' -f2)
    PRIVATE_KEY=$(grep "^TAKAHE_VAPID_PRIVATE_KEY=" development.env | cut -d'"' -f2)
    
    if [ ${#PUBLIC_KEY} -gt 80 ] && [ ${#PRIVATE_KEY} -gt 40 ]; then
        echo -e "  ${GREEN}✓${NC} Claves VAPID configuradas"
        echo "    Public: ${PUBLIC_KEY:0:30}..."
        echo "    Private: ${PRIVATE_KEY:0:30}..."
    else
        echo -e "  ${RED}✗${NC} Claves VAPID parecen incorrectas (muy cortas)"
        exit 1
    fi
else
    echo -e "  ${RED}✗${NC} Claves VAPID no encontradas en development.env"
    exit 1
fi

# Check 2: Format validation
echo ""
echo "[2/5] Validando formato de claves..."
source .venv/bin/activate
FORMAT_CHECK=$(python3 << EOF
import base64
public = "$PUBLIC_KEY"
private = "$PRIVATE_KEY"

# Check URL-safe characters
has_urlsafe = '-' in public or '_' in public
has_unsafe = '+' in public or '/' in public

if has_urlsafe and not has_unsafe:
    # Check lengths
    pub_bytes = base64.urlsafe_b64decode(public + '==')
    priv_bytes = base64.urlsafe_b64decode(private + '==')
    if len(pub_bytes) == 65 and len(priv_bytes) == 32:
        print("OK")
    else:
        print("WRONG_LENGTH")
else:
    print("WRONG_FORMAT")
EOF
)

if [ "$FORMAT_CHECK" = "OK" ]; then
    echo -e "  ${GREEN}✓${NC} Formato base64url correcto"
    echo "    Public: 65 bytes (uncompressed point)"
    echo "    Private: 32 bytes (EC private key)"
else
    echo -e "  ${RED}✗${NC} Formato incorrecto: $FORMAT_CHECK"
    exit 1
fi

# Check 3: Dependencies installed
echo ""
echo "[3/5] Verificando dependencias Python..."
if python3 -c "import django, pywebpush, pydantic" 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} Django, pywebpush, pydantic instalados"
else
    echo -e "  ${RED}✗${NC} Faltan dependencias"
    echo "    Ejecuta: pip install -r requirements.txt"
    exit 1
fi

# Check 4: Database running
echo ""
echo "[4/5] Verificando PostgreSQL..."
if docker ps | grep -q postgres; then
    echo -e "  ${GREEN}✓${NC} PostgreSQL corriendo"
else
    echo -e "  ${YELLOW}⚠${NC}  PostgreSQL no está corriendo"
    echo "    Inicia con: docker compose -f docker/docker-compose.yml up -d db"
fi

# Check 5: Verify utilities exist
echo ""
echo "[5/5] Verificando archivos del proyecto..."
FILES=(
    "core/vapid_utils.py"
    "activities/services/push_notifications.py"
    "api/views/push.py"
    "api/schemas.py"
)

ALL_OK=true
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ${GREEN}✓${NC} $file"
    else
        echo -e "  ${RED}✗${NC} $file no encontrado"
        ALL_OK=false
    fi
done

if [ "$ALL_OK" = false ]; then
    exit 1
fi

echo ""
echo "=========================================================================="
echo -e "  ${GREEN}TODO LISTO${NC}"
echo "=========================================================================="
echo ""
echo "Próximos pasos:"
echo ""
echo "1. Inicia el servidor Takahe:"
echo "   ./start_server.sh"
echo ""
echo "2. Verifica la API (en otra terminal):"
echo "   curl http://localhost:8000/api/v2/instance | jq '.configuration.vapid'"
echo ""
echo "3. En Elk:"
echo "   - Cierra sesión"
echo "   - Vuelve a iniciar sesión"
echo "   - Settings → Notifications → Push Notifications"
echo "   - Click en 'Habilitar notificaciones push'"
echo ""
echo "=========================================================================="
