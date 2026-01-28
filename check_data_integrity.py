#!/usr/bin/env python
"""
Script para verificar la integridad de datos en la base de datos de Takahe.
Encuentra posts con autores sin dominio asociado.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "takahe.settings")
django.setup()

from activities.models import Post
from users.models import Identity


def check_posts_without_author_domain():
    """Encuentra posts cuyos autores no tienen dominio."""
    print("Buscando posts con autores sin dominio...")
    
    # Posts con autor None
    posts_no_author = Post.objects.filter(author__isnull=True)
    count_no_author = posts_no_author.count()
    
    if count_no_author > 0:
        print(f"⚠️  Encontrados {count_no_author} posts SIN AUTOR:")
        for post in posts_no_author[:10]:
            print(f"   - Post ID: {post.pk}, URI: {post.object_uri}")
        if count_no_author > 10:
            print(f"   ... y {count_no_author - 10} más")
    else:
        print("✓ No se encontraron posts sin autor")
    
    # Posts cuyo autor no tiene dominio
    posts_no_domain = Post.objects.filter(author__domain__isnull=True)
    count_no_domain = posts_no_domain.count()
    
    if count_no_domain > 0:
        print(f"\n⚠️  Encontrados {count_no_domain} posts con autor SIN DOMINIO:")
        for post in posts_no_domain.select_related('author')[:10]:
            print(f"   - Post ID: {post.pk}, Autor: {post.author.username if post.author else 'N/A'}")
        if count_no_domain > 10:
            print(f"   ... y {count_no_domain - 10} más")
    else:
        print("✓ No se encontraron posts con autores sin dominio")
    
    return count_no_author, count_no_domain


def check_identities_without_domain():
    """Encuentra identidades sin dominio."""
    print("\nBuscando identidades sin dominio...")
    
    identities_no_domain = Identity.objects.filter(domain__isnull=True)
    count = identities_no_domain.count()
    
    if count > 0:
        print(f"⚠️  Encontradas {count} identidades SIN DOMINIO:")
        for identity in identities_no_domain[:10]:
            print(f"   - Identity ID: {identity.pk}, Username: {identity.username}")
        if count > 10:
            print(f"   ... y {count - 10} más")
    else:
        print("✓ No se encontraron identidades sin dominio")
    
    return count


def main():
    print("=" * 60)
    print("Verificación de integridad de datos de Takahe")
    print("=" * 60)
    print()
    
    posts_no_author, posts_no_domain = check_posts_without_author_domain()
    identities_no_domain = check_identities_without_domain()
    
    print("\n" + "=" * 60)
    print("RESUMEN:")
    print(f"  - Posts sin autor: {posts_no_author}")
    print(f"  - Posts con autor sin dominio: {posts_no_domain}")
    print(f"  - Identidades sin dominio: {identities_no_domain}")
    
    if posts_no_author + posts_no_domain + identities_no_domain > 0:
        print("\n⚠️  Se encontraron problemas de integridad de datos.")
        print("Estos deberían ser corregidos para evitar errores.")
        print("\nPara eliminar posts problemáticos, puedes usar:")
        print("  python manage.py shell")
        print("  >>> from activities.models import Post")
        print("  >>> Post.objects.filter(author__isnull=True).delete()")
        print("  >>> Post.objects.filter(author__domain__isnull=True).delete()")
    else:
        print("\n✓ No se encontraron problemas de integridad de datos.")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
