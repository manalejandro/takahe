# Correcciones Aplicadas - AttributeError uri_domain

## Problema
`AttributeError: 'NoneType' object has no attribute 'uri_domain'` en `/api/v1/timelines/public`

## Archivos Corregidos

### 1. `/api/views/timelines.py`
- ✅ Agregado `select_related("author", "author__domain")` en endpoints:
  - `public()`
  - `hashtag()`
  - `favourites()`

### 2. `/activities/models/post.py`
- ✅ Línea ~376: Método `get_hostname()` - verifica `author.domain` antes de acceder a `uri_domain`
- ✅ Línea ~703: Serialización ActivityPub de hashtags - verifica `author.domain`
- ✅ Línea ~1193: Serialización Mastodon de hashtags - verifica `author.domain`

### 3. `/core/html.py` ⭐ **CAUSA PRINCIPAL DEL ERROR**
- ✅ Línea ~343: `render_post()` - verifica `post.author.domain` antes de acceder a `uri_domain`
- ✅ Línea ~358: `render_identity_summary()` - verifica `identity.domain`
- ✅ Línea ~373: `render_identity_data()` - verifica `identity.domain`

### 4. `/users/models/identity.py`
- ✅ Línea ~307: Método `get_hostname()` - verifica `domain`
- ✅ Línea ~320: Método `absolute_profile_uri()` - verifica `domain`
- ✅ Línea ~332: Método `all_absolute_profile_uris()` - verifica `domain`
- ✅ Línea ~392: Método `generate_keypair()` - verifica `domain` antes de asignar `shared_inbox_uri`

### 5. `/core/uris.py`
- ✅ Línea ~38: Clase `AutoAbsoluteUrl` - verifica `identity.domain` antes de acceder a `uri_domain`

## Pasos para Aplicar

1. **Reiniciar el servidor:**
   ```bash
   # Si usas el script de inicio
   ./start_server.sh
   
   # O si corres manualmente
   pkill -f "python.*manage.py"
   python manage.py runserver
   ```

2. **Verificar integridad de datos (opcional pero recomendado):**
   ```bash
   python check_data_integrity.py
   ```

3. **Si hay posts con datos corruptos, limpiarlos:**
   ```python
   python manage.py shell
   
   from activities.models import Post
   
   # Ver cuántos posts problemáticos hay
   problematic = Post.objects.filter(author__domain__isnull=True)
   print(f"Posts con autor sin dominio: {problematic.count()}")
   
   # Eliminar posts problemáticos (si es necesario)
   problematic.delete()
   ```

## Resultado Esperado

Después de reiniciar el servidor:
- ✅ El timeline público (`/api/v1/timelines/public`) debería cargar sin errores
- ✅ No más `AttributeError: 'NoneType' object has no attribute 'uri_domain'`
- ✅ El código ahora maneja posts con autores que tienen `domain = None`

## Nota Importante

El error principal estaba en **`core/html.py`** donde el método `render_post()` es llamado por `safe_content_remote()` durante la serialización de posts para la API. Este método intentaba acceder a `post.author.domain.uri_domain` sin verificar si `domain` era `None`.
