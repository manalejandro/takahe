#!/bin/bash
# Script de actualización segura de dependencias para Takahe
# Uso: ./update_dependencies.sh

set -e  # Salir en caso de error

echo "🔄 ACTUALIZACIÓN DE DEPENDENCIAS DE TAKAHE"
echo "=========================================="
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar que estamos en el directorio correcto
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ Error: requirements.txt no encontrado${NC}"
    echo "Asegúrate de ejecutar este script desde el directorio raíz del proyecto"
    exit 1
fi

# Verificar que hay un entorno virtual activo o disponible
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -d ".venv" ]; then
        echo -e "${YELLOW}⚠️  Activando entorno virtual...${NC}"
        source .venv/bin/activate
    else
        echo -e "${RED}❌ Error: No se encontró un entorno virtual${NC}"
        echo "Crea uno con: python -m venv .venv"
        exit 1
    fi
fi

echo "✅ Usando entorno virtual: $VIRTUAL_ENV"
echo ""

# Backup de las dependencias actuales
echo "📦 Creando backup de dependencias actuales..."
pip freeze > requirements.backup.txt
echo "✅ Backup guardado en requirements.backup.txt"
echo ""

# Actualizar pip, setuptools y wheel
echo "🔧 Actualizando herramientas de instalación..."
pip install --upgrade pip setuptools wheel
echo ""

# Instalar dependencias principales
echo "📥 Instalando dependencias principales..."
pip install -r requirements.txt --upgrade
echo ""

# Instalar dependencias de desarrollo si existe el archivo
if [ -f "requirements-dev.txt" ]; then
    echo "📥 Instalando dependencias de desarrollo..."
    pip install -r requirements-dev.txt --upgrade
    echo ""
fi

# Mostrar versiones instaladas
echo "📋 Versiones instaladas:"
echo "------------------------"
pip list | grep -E "(Django|cryptography|Pillow|pydantic|httpx|gunicorn|redis|psycopg|sentry-sdk)"
echo ""

# Verificar vulnerabilidades conocidas con pip-audit (si está disponible)
echo "🔍 Verificando vulnerabilidades conocidas..."
if command -v pip-audit &> /dev/null; then
    pip-audit || true  # No fallar si encuentra vulnerabilidades, solo reportar
else
    echo -e "${YELLOW}⚠️  pip-audit no está instalado${NC}"
    echo "Para análisis de vulnerabilidades, instálalo con: pip install pip-audit"
fi
echo ""

# Verificar configuración de Django
echo "🔍 Verificando configuración de Django..."
if [ -f "manage.py" ]; then
    export TAKAHE_SECRET_KEY="test-key-for-check"
    export TAKAHE_DATABASE_SERVER="sqlite:///test.db"
    export TAKAHE_MAIN_DOMAIN="test.local"
    python manage.py check --deploy 2>&1 | head -20 || true
else
    echo -e "${YELLOW}⚠️  manage.py no encontrado, saltando verificación${NC}"
fi
echo ""

# Ejecutar verificación de seguridad personalizada
echo "🔒 Ejecutando verificación de seguridad personalizada..."
if [ -f "security_check.py" ]; then
    python security_check.py || true
fi
echo ""

# Resumen final
echo "=========================================="
echo -e "${GREEN}✅ ACTUALIZACIÓN COMPLETADA${NC}"
echo "=========================================="
echo ""
echo "📝 Próximos pasos recomendados:"
echo "  1. Revisar los cambios: git diff requirements.txt requirements-dev.txt"
echo "  2. Ejecutar tests: pytest"
echo "  3. Verificar migraciones: python manage.py makemigrations --check"
echo "  4. Revisar SECURITY.md para cambios importantes"
echo "  5. Probar en entorno de desarrollo antes de producción"
echo ""
echo "💾 Si necesitas revertir: pip install -r requirements.backup.txt"
echo ""
