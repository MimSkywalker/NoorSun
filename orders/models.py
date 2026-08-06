from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction

from core.models import TimeStampedModel
from products.models import ProductVariant


import random
import string
from datetime import date


class Cart(TimeStampedModel):

    # Authenticated user (optional for guests)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='carts',
        null=True,
        blank=True,
    )

    # Guest session identifier
    session_key = models.CharField(
        max_length=40, null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        # Optimize cart lookups
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['session_key', 'is_active']),
        ]

    def clean(self):
        # Cart must belong to a user or a guest session
        if not self.user_id and not self.session_key:
            raise ValidationError(
                "سبد خرید باید یا به کاربر یا به session متصل باشد.")

    def __str__(self):
        owner = self.user.phone_number if self.user_id else f"guest:{self.session_key}"
        return f"Cart({owner})"

    @property
    def items_count(self):
        # Total quantity of items
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        # Sum of all item totals
        return sum(item.line_total for item in self.items.all())

    @property
    def shipping_cost(self):
        # Free shipping above threshold
        if self.items_count == 0:
            return 0
        if self.subtotal >= settings.CART_FREE_SHIPPING_THRESHOLD:
            return 0
        return settings.CART_SHIPPING_COST

    @property
    def packaging_cost(self):
        # Fixed packaging fee
        if self.items_count == 0:
            return 0
        return settings.CART_PACKAGING_COST

    @property
    def total(self):
        return self.subtotal + self.shipping_cost + self.packaging_cost


class CartItem(TimeStampedModel):

    # Parent cart
    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name='items')

    # Selected product variant
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        # Prevent duplicate variants in the same cart
        unique_together = ('cart', 'variant')

    def __str__(self):
        return f"{self.variant} x {self.quantity}"

    @property
    # Current unit price
    def unit_price(self):
        return self.variant.final_price

    @property
    def line_total(self):
        # Total price for this item
        return self.unit_price * self.quantity

# Generate a unique order tracking code


def generate_tracking_code():

    date_part = date.today().strftime('%Y%m%d')
    rand_part = ''.join(random.choices(string.digits, k=6))
    return f"ORD-{date_part}-{rand_part}"


class Order(TimeStampedModel):
    """
    Customer order with shipping and pricing snapshots
    """

    # Available order statuses
    class Status(models.TextChoices):
        PENDING = 'pending', 'در انتظار پرداخت'
        PROCESSING = 'processing', 'در حال پردازش'
        SHIPPED = 'shipped', 'ارسال شده'
        DELIVERED = 'delivered', 'تحویل داده شده'
        CANCELLED = 'cancelled', 'لغو شده'
        EXPIRED = 'expired', 'منقضی شده' 

    # Order owner
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='orders'
    )

    # Unique tracking code
    tracking_code = models.CharField(
        max_length=32, unique=True, db_index=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING)

    # Shipping address snapshot
    address_title = models.CharField(max_length=100, blank=True)
    address_full_text = models.TextField()
    address_postal_code = models.CharField(max_length=10)
    address_receiver_name = models.CharField(max_length=150)
    address_receiver_phone = models.CharField(max_length=11)
    address_city_title = models.CharField(max_length=100)
    address_province_title = models.CharField(max_length=100)

    # Price snapshot
    subtotal = models.DecimalField(max_digits=12, decimal_places=0)
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=0)
    packaging_cost = models.DecimalField(max_digits=12, decimal_places=0)
    total = models.DecimalField(max_digits=12, decimal_places=0)

    class Meta:
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['tracking_code']),
        ]
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Generate tracking code automatically
        if not self.tracking_code:
            code = generate_tracking_code()
            while Order.objects.filter(tracking_code=code).exists():
                code = generate_tracking_code()
            self.tracking_code = code
        super().save(*args, **kwargs)

    def __str__(self):
        return self.tracking_code


class OrderItem(models.Model):
    """
    Single purchased item within an order
    """
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='items')

    # Purchased variant
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.SET_NULL, null=True, related_name='order_items'
    )

    product_title = models.CharField(max_length=255)
    variant_info = models.CharField(max_length=255, blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=0)
    quantity = models.PositiveIntegerField()

    @property
    def line_total(self):
        # Calculate total price for this item
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.product_title} x {self.quantity}"


class InsufficientStockError(Exception):
    """
    Raised when requested quantity exceeds available stock
    """

    def __init__(self, variant, available):
        self.variant = variant
        self.available = available
        super().__init__(f"موجودی کافی نیست برای {variant}")


class ProductInactiveError(Exception):
    """
    Raised when a product in the cart is no longer active.
    """

    def __init__(self, product):
        self.product = product
        super().__init__(f"محصول {product} غیرفعال است.")


class VariantInactiveError(Exception):
    """
    Raised when a product variant in the cart is no longer active.
    """

    def __init__(self, variant):
        self.variant = variant
        super().__init__(f"واریانت {variant} غیرفعال است.")


@transaction.atomic
def create_order_from_cart(cart, user, address):
    """
    Finalize the shopping cart by:
    - validating stock
    - creating the order
    - creating order items
    - reducing inventory
    - updating product sales
    - deactivating the cart

    The entire process is atomic. If any step fails,
    all database changes are rolled back.
    """

    items = list(cart.items.select_related(
        'variant', 'variant__product').all())
    if not items:
        raise ValueError("سبد خرید خالی است.")

    # Final validation of product availability and stock before making any changes.
    for item in items:
        variant = ProductVariant.objects.select_for_update().get(pk=item.variant_id)

        if not variant.product.is_active:
            raise ProductInactiveError(variant.product)

        if not variant.is_active:
            raise VariantInactiveError(variant)

        if variant.stock < item.quantity:
            raise InsufficientStockError(variant, variant.stock)

    order = Order.objects.create(
        user=user,
        address_title=address.title,
        address_full_text=address.full_address,
        address_postal_code=address.postal_code,
        address_receiver_name=address.receiver_name,
        address_receiver_phone=address.receiver_phone,
        address_city_title=address.city.title,
        address_province_title=address.city.province.title,
        subtotal=cart.subtotal,
        shipping_cost=cart.shipping_cost,
        packaging_cost=cart.packaging_cost,
        total=cart.total,
    )

    for item in items:
        variant = ProductVariant.objects.select_for_update().get(pk=item.variant_id)
        variant.stock -= item.quantity
        variant.save(update_fields=['stock'])

        variant.product.sales_count += item.quantity
        variant.product.save(update_fields=['sales_count'])

        OrderItem.objects.create(
            order=order,
            variant=variant,
            product_title=variant.product.title,
            variant_info=str(variant),
            unit_price=item.unit_price,
            quantity=item.quantity,
        )

    cart.is_active = False
    cart.save(update_fields=['is_active'])

    return order



class Payment(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'در انتظار'
        SUCCESS = 'success', 'موفق'
        FAILED = 'failed', 'ناموفق'

    order = models.ForeignKey(
        Order, on_delete=models.PROTECT, related_name='payments'
    )
    gateway = models.CharField(max_length=30)
    amount = models.DecimalField(max_digits=12, decimal_places=0) 
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    authority = models.CharField(max_length=100, blank=True, db_index=True)
    ref_id = models.CharField(max_length=100, blank=True)
    raw_response = models.JSONField(blank=True, null=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['authority']),
            models.Index(fields=['order', 'status']),
        ]

    def __str__(self):
        return f'Payment #{self.pk} - {self.order.tracking_code} - {self.get_status_display()}'