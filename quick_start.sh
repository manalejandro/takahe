#!/bin/bash
# Script de inicio rápido para instalar y verificar el proyecto Takahe
# Ejecutar después de actualización de seguridad

set -e

echo "🚀 INSTALACIÓN RÁPIDA DE TAKAHE"
echo "================================"
echo ""

# Verificar Python
echo "1️⃣  Verificando Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✅ $PYTHON_VERSION encontrado"
else
    echo "❌ Python 3 no encontrado. Instálalo primero."
    exit 1
fi
echo ""

# Crear entorno virtual si no existe
if [ ! -d ".venv" ]; then
    echo "2️⃣  Creando entorno virtual..."
    python3 -m venv .venv
    echo "✅ Entorno virtual creado"
else
    echo "2️⃣  Entorno virtual ya existe"
fi
echo ""

# Activar entorno virtual
echo "3️⃣  Activando entorno virtual..."
source .venv/bin/activate
echo "✅ Entorno virtual activado"
echo ""

# Actualizar pip
echo "4️⃣  Actualizando pip..."
pip install --upgrade pip setuptools wheel -q
echo "✅ pip actualizado"
echo ""

# Instalar dependencias
echo "5️⃣  Instalando dependencias (esto puede tardar unos minutos)..."
pip install -r requirements.txt -q
echo "✅ Dependencias instaladas"
echo ""

# Instalar dependencias de desarrollo
echo "6️⃣  Instalando dependencias de desarrollo..."
pip install -r requirements-dev.txt -q
echo "✅ Dependencias de desarrollo instaladas"
echo ""

# Crear archivo .env si no existe
if [ ! -f ".env" ]; then
    echo "7️⃣  Creando archivo .env desde ejemplo..."
    cp .env.example .env
    echo "✅ Archivo .env creado - DEBES EDITARLO antes de usar"
    echo "⚠️  Edita .env y configura al menos:"
    echo "    - TAKAHE_SECRET_KEY"
    echo "    - TAKAHE_MAIN_DOMAIN"
    echo "    - TAKAHE_ALLOWED_HOSTS"
    echo "    - Configuración de base de datos"
else
    echo "7️⃣  Archivo .env ya existe"
fi
echo ""

# Ejecutar verificación de seguridad
echo "8️⃣  Ejecutando verificación de seguridad..."
python security_check.py || true
echo ""

# Mostrar siguientes pasos
echo "================================"
echo "✅ INSTALACIÓN COMPLETADA"
echo "================================"
echo ""
echo "📝 Próximos pasos:"
echo ""
echo "1. Editar configuración:"
echo "   nano .env"
echo ""
echo "2. Configurar base de datos:"
echo "   python manage.py migrate"
echo ""
echo "3. Crear superusuario:"
echo "   python manage.py createsuperuser"
echo ""
echo "4. Colectar archivos estáticos:"
echo "   python manage.py collectstatic"
echo ""
echo "5. Ejecutar tests:"
echo "   pytest"
echo ""
echo "6. Iniciar servidor de desarrollo:"
echo "   python manage.py runserver"
echo ""
echo "7. Para producción, revisar:"
echo "   - SECURITY.md"
echo "   - docs/installation.rst"
echo "   - python manage.py check --deploy"
echo ""
echo "================================"
echo "📚 Documentación adicional:"
echo "  - README.md"
echo "  - SECURITY.md"
echo "  - CHANGELOG_SECURITY.md"
echo "  - docs/installation.rst"
echo "================================"
echo ""
