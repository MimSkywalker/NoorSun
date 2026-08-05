from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Category,
    Brand,
    Attribute,
    AttributeValue,
    Product,
    ProductImage,
    ProductVariant,
)


# -------------------------
# Category And Brand
# -------------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'is_active')
    list_filter = ('is_active', 'parent')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


# -----------------------
# Attribute
# -----------------------
class AttributeValueInline(admin.TabularInline):
    model = AttributeValue
    extra = 1


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    inlines = [AttributeValueInline]


@admin.register(AttributeValue)
class AttributeValueAdmin(admin.ModelAdmin):
    list_display = ('attribute', 'value')
    list_filter = ('attribute',)
    search_fields = ('value',)


# -----------------------
# ProductImageInline
# -----------------------
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'image_preview', 'is_main', 'order')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.pk and obj.image:
            return format_html(
                '<img src="{}" style="height: 60px; border-radius: 4px;" />',
                obj.image.url,
            )
        return "—"
    image_preview.short_description = "پیش‌نمایش"


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = (
        'sku',
        'price',
        'discount_price',
        'stock',
        'is_active',
        'attribute_values',
    )
    filter_horizontal = ('attribute_values',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'category',
        'brand',
        'is_active',
        'total_stock',
        'created_at',
    )
    list_filter = ('is_active', 'category', 'brand')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    autocomplete_fields = ('category', 'brand', 'replacement_product')
    inlines = [ProductImageInline, ProductVariantInline]

    def total_stock(self, obj):
        return sum(v.stock for v in obj.variants.all())
    total_stock.short_description = "موجودی کل"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('variants', 'images')


# -----------------------
# ProductVariant
# -----------------------


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        'sku',
        'product',
        'price',
        'discount_price',
        'final_price',
        'stock',
        'is_active',
        'is_in_stock',)
    list_filter = ('is_active', 'product__category',
                   'product__brand', 'discount_price')
    search_fields = ('sku', 'product__title')
    autocomplete_fields = ('product',)
    filter_horizontal = ('attribute_values',)

    def is_in_stock(self, obj):
        return obj.is_in_stock
    is_in_stock.boolean = True
    is_in_stock.short_description = "موجود؟"
