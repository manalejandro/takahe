# Fix: Conflicto de Dependencias con Pydantic

## Problema Encontrado

Al intentar instalar las dependencias actualizadas, se encontró un conflicto:

```
ERROR: Cannot install -r requirements.txt (line 8) and pydantic~=2.10.5 
because these package versions have conflicting dependencies.

The conflict is caused by:
    The user requested pydantic~=2.10.5
    django-hatchway 0.5.2 depends on pydantic~=1.10
```

## Causa

- **django-hatchway** (dependencia del proyecto) requiere `pydantic~=1.10`
- La actualización inicial intentó migrar a `pydantic 2.10.5`
- No hay versión más reciente de django-hatchway disponible (última: 0.5.2)

## Solución Implementada

✅ **Mantener Pydantic en v1.10.x** en lugar de migrar a v2

### Cambios Realizados

1. **requirements.txt**
   - ✅ Revertido: `pydantic~=2.10.5` → `pydantic~=1.10.18`

2. **takahe/settings.py**
   - ✅ Revertidas importaciones a sintaxis Pydantic v1
   - ✅ Revertido `@field_validator` a `@validator`
   - ✅ Revertido `model_config` a `class Config`

3. **Documentación actualizada**
   - ✅ SECURITY.md: Reflejados cambios correctos
   - ✅ CHANGELOG_SECURITY.md: Eliminadas referencias a migración v2

## Impacto en Seguridad

✅ **Sin impacto negativo**: 
- Pydantic 1.10.18 incluye todas las correcciones de seguridad críticas
- Es la última versión de la rama 1.x
- Mantiene compatibilidad con todo el ecosistema del proyecto

## Versiones Finales de Dependencias Principales

| Paquete | Versión Antes | Versión Después | Estado |
|---------|---------------|-----------------|--------|
| Django | 4.2.0 | 5.1.5 | ✅ Actualizado |
| cryptography | 39.0 | 44.0.0 | ✅ Actualizado |
| Pillow | 9.3.0 | 11.1.0 | ✅ Actualizado |
| **pydantic** | **1.10.2** | **1.10.18** | ✅ Actualizado (mantenido en v1) |
| httpx | 0.23 | 0.28.1 | ✅ Actualizado |
| gunicorn | 20.1.0 | 23.0.0 | ✅ Actualizado |
| redis | 4.4.0 | 5.2.1 | ✅ Actualizado |
| psycopg | 3.1.8 | 3.2.4 | ✅ Actualizado |

## Verificación

```bash
# 1. Limpiar instalaciones previas
pip uninstall -y pydantic pydantic-settings django-hatchway

# 2. Instalar dependencias actualizadas
pip install -r requirements.txt

# 3. Verificar versiones
pip show pydantic django-hatchway

# 4. Verificar configuración
python -m py_compile takahe/settings.py
```

## Alternativas Consideradas

### ❌ Opción 1: Forzar Pydantic v2
- **Problema**: Requeriría fork o reemplazo de django-hatchway
- **Esfuerzo**: Alto - refactoring extenso
- **Riesgo**: Medio-Alto

### ✅ Opción 2: Mantener Pydantic v1 (ELEGIDA)
- **Ventaja**: Compatibilidad total
- **Esfuerzo**: Bajo
- **Riesgo**: Muy bajo
- **Seguridad**: Mantenida (v1.10.18 tiene todos los fixes)

## Próximos Pasos

Para migrar a Pydantic v2 en el futuro:
1. Esperar actualización de django-hatchway a v2-compatible
2. O considerar reemplazar django-hatchway con alternativa
3. O contribuir PR a django-hatchway para soporte de Pydantic v2

## Referencias

- [django-hatchway PyPI](https://pypi.org/project/django-hatchway/)
- [Pydantic v1 Release Notes](https://docs.pydantic.dev/1.10/)
- [Pydantic v2 Migration Guide](https://docs.pydantic.dev/latest/migration/)

---

**Fecha**: 19 de enero de 2026  
**Estado**: ✅ Resuelto  
**Impacto en Seguridad**: Ninguno - Todas las actualizaciones de seguridad mantenidas
