from django.db.models import Q, Min


def filter_products(base_queryset, params):
    """
    Filter and sort products based on the provided query parameters.

    Supported filters:
    - Search keyword
    - Category
    - Brand
    - Dynamic product attributes
    - Price range

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

    # Start with active products only.
    qs = base_queryset.filter(is_active=True)

    # Search by product title or description.
    q = (params.get('q') or '').strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

    category_slug = params.get('category')
    if category_slug:
        qs = qs.filter(category__slug=category_slug)

    brand_slug = params.get('brand')
    if brand_slug:
        qs = qs.filter(brand__slug=brand_slug)


    # Apply dynamic attribute filters.
    # Expected query string format:
    # attr_<attribute_id>=<value_id>
    # Example:
    # ?attr_3=12&attr_3=15&attr_7=20
    attr_filter_applied = False
    for key in params.keys():
        if not key.startswith('attr_'):
            continue
        try:
            attribute_id = int(key.split('_', 1)[1])
        except (ValueError, IndexError):
            continue

        value_ids = params.getlist(key) if hasattr(
            params, 'getlist') else [params.get(key)]
        value_ids = [v for v in value_ids if v]
        if not value_ids:
            continue


        # Keep products that have at least one of the selected values
        # for the current attribu
        qs = qs.filter(
            variants__attribute_values__attribute_id=attribute_id,
            variants__attribute_values__id__in=value_ids,
        )
        attr_filter_applied = True
    
    # Filter by minimum and maximum variant price.
    min_price = params.get('min_price')
    max_price = params.get('max_price')
    if min_price:
        qs = qs.filter(variants__price__gte=min_price)
    if max_price:
        qs = qs.filter(variants__price__lte=max_price)

    if attr_filter_applied or min_price or max_price:
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
        qs = qs.order_by('-created_at')

    return qs
