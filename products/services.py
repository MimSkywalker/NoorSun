from .models import Product
from django.utils import timezone
from .models import Campaign
from django.db.models import Prefetch
from products.models import ProductVariant

# Default number of products displayed in special sections.
SPECIAL_SECTION_LIMIT = 8


def _base_qs():
    """
    Return the base optimized queryset used by all product services.
    """
    return Product.objects.filter(is_active=True) \
        .select_related('category', 'brand') \
        .prefetch_related('images', 'variants')


def get_new_products(limit=SPECIAL_SECTION_LIMIT):
    """
    Return the most recently created active products.
    """
    return _base_qs().order_by('-created_at')[:limit]


def get_bestselling_products(limit=SPECIAL_SECTION_LIMIT):
    """
    Return the best-selling active products.
    """
    return _base_qs().order_by('-sales_count')[:limit]


def get_discounted_products(limit=SPECIAL_SECTION_LIMIT):
    """
    Return active products that have at least one discounted variant.
    """
    return _base_qs().filter(variants__discount_price__isnull=False) \
        .distinct().order_by('-created_at')[:limit]


def get_similar_products(product, limit=SPECIAL_SECTION_LIMIT):
    """
    Return similar products.

    Priority:
    1. Products from the same category.
    2. If not enough results are found, fill the remaining slots
       with products from the same brand.

    The current product is always excluded, and duplicate products
    are prevented.
    """

    # Get products from the same category.
    same_category = list(
        _base_qs().filter(category=product.category).exclude(
            pk=product.pk)[:limit]
    )

    # Fill remaining slots with products from the same brand.
    if len(same_category) < limit and product.brand_id:
        remaining = limit - len(same_category)

        # Exclude the current product and already selected products.
        exclude_ids = [p.pk for p in same_category] + [product.pk]
        same_brand = list(
            _base_qs().filter(brand=product.brand)
            .exclude(pk__in=exclude_ids)[:remaining]
        )
        same_category += same_brand

    return same_category


def attach_campaign_prices(products):
    """
    Precompute campaign prices once to avoid N+1 queries per variant.
    """

    now = timezone.now()
    active_campaigns = list(
        Campaign.objects.filter(
            is_active=True, start_at__lte=now, end_at__gte=now)
        .prefetch_related('categories', 'brands', 'products')
    )

    if not active_campaigns:
        return list(products)

    products = list(products)
    for product in products:
        for variant in product.variants.all():
            variant.product = product
            best_price = None
            for campaign in active_campaigns:
                if campaign.covers_variant(variant):
                    price = campaign.price_for(variant)
                    if best_price is None or price < best_price:
                        best_price = price
            variant._campaign_price_cache = best_price

    return products
