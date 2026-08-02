from django.db.models import Q, Min


def filter_products(base_queryset, params):
    """
    Filter and sort products based on query parameters.

    Supported filters:
    - Search keyword (title or description)
    - Category
    - Brand
    - Color
    - Size
    - Minimum price
    - Maximum price

    Supported sorting:
    - newest (default)
    - cheapest
    - expensive
    - bestselling

    Args:
        base_queryset: Initial Product queryset.
        params: Query parameters (typically request.GET).

    Returns:
        A filtered and ordered Product queryset.
    """
    qs = base_queryset.filter(is_active=True)

    q = (params.get('q') or '').strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

    category_slug = params.get('category')
    if category_slug:
        qs = qs.filter(category__slug=category_slug)

    brand_slug = params.get('brand')
    if brand_slug:
        qs = qs.filter(brand__slug=brand_slug)

    color_id = params.get('color')
    size_id = params.get('size')
    if color_id:
        qs = qs.filter(variants__attribute_values__id=color_id)
    if size_id:
        qs = qs.filter(variants__attribute_values__id=size_id)

    min_price = params.get('min_price')
    max_price = params.get('max_price')
    if min_price:
        qs = qs.filter(variants__price__gte=min_price)
    if max_price:
        qs = qs.filter(variants__price__lte=max_price)

    # Remove duplicate products caused by joins with variants.
    if any([color_id, size_id, min_price, max_price]):
        qs = qs.distinct()

    sort = params.get('sort', 'newest')
    if sort == 'cheapest':
        qs = qs.annotate(_min_price=Min('variants__price')
                         ).order_by('_min_price')
    elif sort == 'expensive':
        qs = qs.annotate(_min_price=Min('variants__price')
                         ).order_by('-_min_price')
    elif sort == 'bestselling':
        qs = qs.order_by('-sales_count')
    else:
        # Default: newest products first.
        qs = qs.order_by('-created_at')

    return qs
