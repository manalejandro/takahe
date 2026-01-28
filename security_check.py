#!/usr/bin/env python
"""
Security Configuration Checker for Takahe
Verifica que la configuración de seguridad esté correctamente establecida.
"""
import os
import sys

def check_environment_variables():
    """Verifica variables de entorno críticas de seguridad"""
    issues = []
    warnings = []
    
    # Variables obligatorias en producción
    required_vars = {
        "TAKAHE_SECRET_KEY": "Llave secreta para firmar sesiones",
        "TAKAHE_MAIN_DOMAIN": "Dominio principal de la aplicación",
        "TAKAHE_ALLOWED_HOSTS": "Hosts permitidos para prevenir Host Header Injection",
    }
    
    # Variables recomendadas
    recommended_vars = {
        "TAKAHE_DATABASE_SERVER": "Configuración de base de datos",
        "TAKAHE_USE_PROXY_HEADERS": "Si estás detrás de un proxy/load balancer",
        "TAKAHE_CORS_HOSTS": "Hosts permitidos para CORS",
        "TAKAHE_CSRF_HOSTS": "Hosts de confianza para CSRF",
    }
    
    print("🔒 VERIFICACIÓN DE SEGURIDAD DE TAKAHE\n")
    print("=" * 60)
    
    # Verificar variables obligatorias
    print("\n📋 Variables Obligatorias:")
    for var, description in required_vars.items():
        value = os.environ.get(var)
        if not value:
            issues.append(f"❌ {var}: NO CONFIGURADA")
            print(f"  ❌ {var}: NO CONFIGURADA")
            print(f"     {description}")
        elif var == "TAKAHE_SECRET_KEY" and value.startswith("autokey-"):
            issues.append(f"❌ {var}: Usando clave automática (inseguro en producción)")
            print(f"  ❌ {var}: Usando clave automática (inseguro en producción)")
        elif var == "TAKAHE_MAIN_DOMAIN" and value == "example.com":
            issues.append(f"❌ {var}: Usando dominio de ejemplo")
            print(f"  ❌ {var}: Usando dominio de ejemplo")
        elif var == "TAKAHE_ALLOWED_HOSTS" and value == "*":
            issues.append(f"⚠️  {var}: Permitiendo todos los hosts (inseguro)")
            print(f"  ⚠️  {var}: Permitiendo todos los hosts (inseguro)")
        else:
            print(f"  ✅ {var}: Configurada")
    
    # Verificar variables recomendadas
    print("\n💡 Variables Recomendadas:")
    for var, description in recommended_vars.items():
        value = os.environ.get(var)
        if not value:
            warnings.append(f"⚠️  {var}: No configurada")
            print(f"  ⚠️  {var}: No configurada")
            print(f"     {description}")
        else:
            print(f"  ✅ {var}: Configurada")
    
    # Verificar modo DEBUG
    print("\n🐛 Modo de Ejecución:")
    debug_mode = os.environ.get("TAKAHE_DEBUG", "False").lower() in ("true", "1", "yes")
    if debug_mode:
        warnings.append("⚠️  DEBUG: Activado (desactívalo en producción)")
        print("  ⚠️  DEBUG: Activado (desactívalo en producción)")
    else:
        print("  ✅ DEBUG: Desactivado")
    
    # Resumen
    print("\n" + "=" * 60)
    print("\n📊 RESUMEN:")
    
    if issues:
        print(f"\n❌ PROBLEMAS CRÍTICOS ENCONTRADOS ({len(issues)}):")
        for issue in issues:
            print(f"  {issue}")
        print("\n⚠️  NO DESPLEGAR EN PRODUCCIÓN HASTA RESOLVER ESTOS PROBLEMAS")
    else:
        print("\n✅ No se encontraron problemas críticos")
    
    if warnings:
        print(f"\n⚠️  ADVERTENCIAS ({len(warnings)}):")
        for warning in warnings:
            print(f"  {warning}")
    
    print("\n" + "=" * 60)
    
    # Verificar archivos de configuración
    print("\n📁 Archivos de Configuración:")
    config_files = [".env", "test.env", "development.env"]
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"  ℹ️  Encontrado: {config_file}")
        else:
            print(f"  ⚠️  No encontrado: {config_file}")
    
    print("\n" + "=" * 60)
    print("\n📚 Documentación:")
    print("  • Revisa SECURITY.md para más información")
    print("  • Documentación: docs/installation.rst")
    print("  • Django Deployment Checklist: python manage.py check --deploy")
    
    print("\n" + "=" * 60)
    
    # Retornar código de salida
    if issues:
        return 1
    return 0


def check_dependencies():
    """Verifica que las dependencias críticas estén instaladas"""
    print("\n\n🔧 VERIFICACIÓN DE DEPENDENCIAS\n")
    print("=" * 60)
    
    critical_packages = [
        "django",
        "cryptography",
        "pydantic",
        "pydantic_settings",
        "httpx",
        "psycopg",
    ]
    
    missing = []
    outdated_info = []
    
    for package in critical_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"  ✅ {package}: Instalado")
        except ImportError:
            missing.append(package)
            print(f"  ❌ {package}: NO INSTALADO")
    
    if missing:
        print(f"\n❌ Paquetes faltantes: {', '.join(missing)}")
        print("   Ejecuta: pip install -r requirements.txt")
        return 1
    else:
        print("\n✅ Todas las dependencias críticas están instaladas")
    
    return 0


def main():
    """Ejecuta todas las verificaciones"""
    print("\n" + "🛡️  " * 20)
    print("VERIFICACIÓN DE SEGURIDAD DE TAKAHE")
    print("🛡️  " * 20 + "\n")
    
    env_check = check_environment_variables()
    dep_check = check_dependencies()
    
    print("\n\n" + "=" * 60)
    if env_check == 0 and dep_check == 0:
        print("✅ TODAS LAS VERIFICACIONES PASARON")
        print("=" * 60 + "\n")
        return 0
    else:
        print("❌ ALGUNAS VERIFICACIONES FALLARON")
        print("=" * 60 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
