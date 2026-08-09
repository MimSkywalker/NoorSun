from django.contrib import admin
from .models import Cart, CartItem, Order, OrderItem, Payment, RefundRequest


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session_key',
                    'is_active', 'items_count', 'total')
    list_filter = ('is_active',)
    inlines = [CartItemInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('variant', 'product_title',
                       'variant_info', 'unit_price', 'quantity')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('tracking_code', 'user', 'status', 'total', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('tracking_code', 'user__phone_number')
    readonly_fields = ('tracking_code', 'subtotal',
                       'shipping_cost', 'packaging_cost', 'total')
    inlines = [OrderItemInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'gateway', 'amount', 'status',
                    'authority', 'ref_id', 'paid_at')
    list_filter = ('gateway', 'status')
    search_fields = ('order__tracking_code', 'authority', 'ref_id')
    readonly_fields = ('order', 'gateway', 'amount',
                       'authority', 'ref_id', 'raw_response', 'paid_at')


@admin.register(RefundRequest)
class RefundRequestAdmin(admin.ModelAdmin):
    list_display = ('order', 'user', 'refund_amount',
                    'status', 'created_at', 'processed_at')
    list_filter = ('status',)
    search_fields = ('order__tracking_code', 'user__phone_number')
    readonly_fields = ('order', 'payment', 'user', 'reason',
                       'refund_amount', 'created_at')
    fields = (
        'order', 'payment', 'user', 'reason', 'refund_amount',
        'status', 'admin_note', 'processed_at', 'created_at',
    )
