from django.contrib import admin, messages
from django.utils.html import format_html
from django.http import HttpResponseRedirect

from .models import (
    Category,
    Brand,
    Attribute,
    AttributeValue,
    Product,
    ProductImage,
    ProductVariant,
    Campaign,
    RestockRequest,
    StockMovement,
    Review
)

from .forms import StockMovementAdminForm

from products.stock import record_stock_movement


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
        'sales_count',
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
# ProductVariant and LowStockFilter
# -----------------------


class LowStockFilter(admin.SimpleListFilter):
    title = 'موجودی کم'
    parameter_name = 'low_stock'

    def lookups(self, request, model_admin):
        return (('yes', 'فقط موجودی کم'),)

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            ids = [v.pk for v in queryset if v.is_low_stock]
            return queryset.filter(pk__in=ids)
        return queryset


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
        'is_in_stock',
        'low_stock_alert_sent')
    list_filter = ('is_active', 'product__category',
                   'product__brand', 'discount_price', LowStockFilter)

    search_fields = ('sku', 'product__title')
    autocomplete_fields = ('product',)
    filter_horizontal = ('attribute_values',)

    def is_in_stock(self, obj):
        return obj.is_in_stock
    is_in_stock.boolean = True
    is_in_stock.short_description = "موجود؟"


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('title', 'discount_type', 'value',
                    'start_at', 'end_at', 'is_active', 'is_running')
    list_filter = ('is_active', 'discount_type')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('categories', 'brands', 'products')
    list_editable = ('is_active',)

    def is_running(self, obj):
        return obj.is_running
    is_running.boolean = True
    is_running.short_description = 'در حال اجرا'


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    form = StockMovementAdminForm
    list_display = ('variant', 'movement_type', 'quantity_change',
                    'stock_after', 'order', 'created_by', 'created_at')
    list_filter = ('movement_type',)
    search_fields = ('variant__sku', 'variant__product__title')
    autocomplete_fields = ('variant', 'order')
    readonly_fields = ('stock_after',)

    def has_change_permission(self, request, obj=None):
        return False  # Disable editing historical records.

    def save_model(self, request, obj, form, change):
        if change:
            return  # Prevent updates as an extra safety check.

        try:
            movement = record_stock_movement(
                variant=obj.variant,
                quantity_change=obj.quantity_change,
                movement_type=obj.movement_type,
                note=obj.note,
                order=obj.order,
                user=request.user,
            )
        except ValueError as e:
            # Handle stock validation errors safely.
            request._stock_movement_error = str(e)
            return

        # Sync the admin object with the created movement.
        obj.pk = movement.pk
        obj.id = movement.pk
        obj.stock_after = movement.stock_after
        obj.created_by = movement.created_by
        obj.created_at = movement.created_at
        obj.updated_at = movement.updated_at

    def response_add(self, request, obj, post_url_continue=None):
        error = getattr(request, '_stock_movement_error', None)
        if error:
            self.message_user(request, error, level=messages.ERROR)
            # Return to the add form when movement creation fails.
            return HttpResponseRedirect(request.path)

        return super().response_add(request, obj, post_url_continue)


@admin.register(RestockRequest)
class RestockRequestAdmin(admin.ModelAdmin):
    list_display = ('variant', 'phone_number', 'email',
                    'user', 'is_notified', 'created_at')
    list_filter = ('is_notified',)
    search_fields = ('variant__product__title', 'phone_number', 'email')
    readonly_fields = ('variant', 'user', 'phone_number',
                       'email', 'is_notified', 'notified_at', 'created_at')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'display_name', 'rating',
                    'is_approved', 'created_at')
    list_filter = ('is_approved', 'rating')
    search_fields = ('product__title', 'guest_name',
                     'user__phone_number', 'text')
    autocomplete_fields = ('product', 'user')
    readonly_fields = ('user', 'guest_name', 'rating', 'text', 'created_at')
    fields = (
        'product', 'user', 'guest_name', 'rating', 'text',
        'is_approved', 'admin_reply', 'admin_replied_at', 'created_at',
    )
    actions = ['approve_reviews', 'unapprove_reviews']

    list_editable = ['is_approved']

    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"{updated} نظر تأیید شد.")
    approve_reviews.short_description = "تأیید نظرات انتخاب‌شده"

    def unapprove_reviews(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f"{updated} نظر لغو تأیید شد.")
    unapprove_reviews.short_description = "لغو تأیید نظرات انتخاب‌شده"
