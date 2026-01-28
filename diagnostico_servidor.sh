#!/bin/bash
# Diagnóstico para social.manalejandro.com

echo "=== DIAGNÓSTICO DEL SERVIDOR TAKAHE ==="
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. Verificar branch actual
echo -e "${YELLOW}1. Branch actual:${NC}"
git branch | grep '*'
echo ""

# 2. Verificar último commit
echo -e "${YELLOW}2. Último commit:${NC}"
git log --oneline -1
echo ""

# 3. Verificar que push.py existe y tiene el contenido correcto
echo -e "${YELLOW}3. Verificando api/views/push.py:${NC}"
if [ -f "api/views/push.py" ]; then
    echo -e "${GREEN}✓ Archivo existe${NC}"
    line_count=$(wc -l < api/views/push.py)
    echo "  Líneas: $line_count"
    
    if grep -q "def get_subscription" api/views/push.py; then
        echo -e "${GREEN}✓ Función get_subscription encontrada${NC}"
    else
        echo -e "${RED}✗ Función get_subscription NO encontrada${NC}"
    fi
else
    echo -e "${RED}✗ Archivo NO existe${NC}"
fi
echo ""

# 4. Verificar que las rutas están en urls.py
echo -e "${YELLOW}4. Verificando rutas en api/urls.py:${NC}"
if grep -q "v1/push/subscription" api/urls.py; then
    echo -e "${GREEN}✓ Ruta push/subscription encontrada${NC}"
    echo "  Contexto:"
    grep -A3 "v1/push/subscription" api/urls.py
else
    echo -e "${RED}✗ Ruta push/subscription NO encontrada${NC}"
fi
echo ""

# 5. Verificar import de push en urls.py
echo -e "${YELLOW}5. Verificando import de push:${NC}"
if grep -q "^.*push," api/urls.py; then
    echo -e "${GREEN}✓ Import de push encontrado${NC}"
else
    echo -e "${RED}✗ Import de push NO encontrado${NC}"
fi
echo ""

# 6. Verificar variables VAPID
echo -e "${YELLOW}6. Verificando variables VAPID en .env:${NC}"
if [ -f ".env" ]; then
    if grep -q "TAKAHE_VAPID_PUBLIC_KEY" .env; then
        echo -e "${GREEN}✓ VAPID_PUBLIC_KEY encontrada${NC}"
        # Mostrar primeros caracteres
        grep "TAKAHE_VAPID_PUBLIC_KEY" .env | cut -c1-50
    else
        echo -e "${RED}✗ VAPID_PUBLIC_KEY NO encontrada${NC}"
    fi
    
    if grep -q "TAKAHE_VAPID_PRIVATE_KEY" .env; then
        echo -e "${GREEN}✓ VAPID_PRIVATE_KEY encontrada${NC}"
    else
        echo -e "${RED}✗ VAPID_PRIVATE_KEY NO encontrada${NC}"
    fi
else
    echo -e "${RED}✗ Archivo .env NO existe${NC}"
fi
echo ""

# 7. Verificar core/vapid_utils.py
echo -e "${YELLOW}7. Verificando core/vapid_utils.py:${NC}"
if [ -f "core/vapid_utils.py" ]; then
    echo -e "${GREEN}✓ Archivo existe${NC}"
else
    echo -e "${RED}✗ Archivo NO existe (necesario para conversión de claves)${NC}"
fi
echo ""

# 8. Verificar dependencias
echo -e "${YELLOW}8. Verificando dependencias:${NC}"
if pip show pywebpush > /dev/null 2>&1; then
    version=$(pip show pywebpush | grep Version | cut -d' ' -f2)
    echo -e "${GREEN}✓ pywebpush instalado (v$version)${NC}"
else
    echo -e "${RED}✗ pywebpush NO instalado${NC}"
fi

if pip show py-vapid > /dev/null 2>&1; then
    version=$(pip show py-vapid | grep Version | cut -d' ' -f2)
    echo -e "${GREEN}✓ py-vapid instalado (v$version)${NC}"
else
    echo -e "${RED}✗ py-vapid NO instalado${NC}"
fi
echo ""

# 9. Verificar proceso de Django
echo -e "${YELLOW}9. Verificando procesos de Django:${NC}"
if pgrep -f "python.*manage.py" > /dev/null; then
    echo -e "${GREEN}✓ Proceso Django encontrado${NC}"
    ps aux | grep "python.*manage.py" | grep -v grep
else
    echo -e "${RED}✗ Proceso Django NO encontrado${NC}"
    echo "  El servidor necesita reiniciarse"
fi
echo ""

# 10. Probar la ruta localmente
echo -e "${YELLOW}10. Probando ruta push localmente:${NC}"
if command -v curl > /dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/push/subscription 2>/dev/null)
    
    if [ "$HTTP_CODE" == "401" ]; then
        echo -e "${GREEN}✓ Ruta responde 401 (necesita auth) - CORRECTO${NC}"
    elif [ "$HTTP_CODE" == "404" ]; then
        echo -e "${RED}✗ Ruta responde 404 - INCORRECTO${NC}"
    elif [ "$HTTP_CODE" == "000" ]; then
        echo -e "${YELLOW}⚠ No se pudo conectar (¿servidor apagado?)${NC}"
    else
        echo -e "${YELLOW}⚠ Código inesperado: $HTTP_CODE${NC}"
    fi
else
    echo "curl no disponible"
fi
echo ""

# 11. Verificar logs recientes
echo -e "${YELLOW}11. Últimas líneas de logs (si existen):${NC}"
if [ -f "logs/error.log" ]; then
    echo "Últimas 5 líneas de error.log:"
    tail -5 logs/error.log
elif [ -f "takahe.log" ]; then
    echo "Últimas 5 líneas de takahe.log:"
    tail -5 takahe.log
else
    echo "No se encontraron archivos de log en ubicación estándar"
    echo "Verifica con: journalctl -u takahe -n 20"
fi
echo ""

echo "=== FIN DEL DIAGNÓSTICO ==="
echo ""
echo -e "${YELLOW}ACCIONES RECOMENDADAS:${NC}"
echo "1. Si hay errores arriba, corrígelos"
echo "2. Reinicia el servidor: systemctl restart takahe (o tu método)"
echo "3. Verifica logs: journalctl -u takahe -f"
echo "4. Prueba: curl -I https://social.manalejandro.com/api/v1/push/subscription"
