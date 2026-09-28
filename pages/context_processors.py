from .services import get_nav_pages


def static_pages_nav(request):
    pages = get_nav_pages()
    return {
        'menu_pages': [p for p in pages if p['in_menu']],
        'footer_pages': [p for p in pages if p['in_footer']],
    }