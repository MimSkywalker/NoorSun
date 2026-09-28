from django.core.cache import cache
from django.db.models import Q

from .models import StaticPage

NAV_CACHE_KEY = 'pages:nav'
NAV_CACHE_SECONDS = 600


def get_nav_pages():
    data = cache.get(NAV_CACHE_KEY)
    if data is None:
        pages = StaticPage.objects.filter(is_active=True).filter(
            Q(show_in_menu=True) | Q(show_in_footer=True)
        )
        data = [
            {
                'title': p.title,
                'url': p.get_absolute_url(),
                'in_menu': p.show_in_menu,
                'in_footer': p.show_in_footer,
            }
            for p in pages
        ]
        cache.set(NAV_CACHE_KEY, data, NAV_CACHE_SECONDS)
    return data


def invalidate_nav_cache():
    cache.delete(NAV_CACHE_KEY)