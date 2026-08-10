import logging
import random
import secrets
import string
from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone

from core.models import TimeStampedModel
from products.models import ProductVariant

logger = logging.getLogger(__name__)


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
        ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items'
    )

    product = models.ForeignKey(
        'products.Product', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='order_items',
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
            product=variant.product,
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


class RefundRequest(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'در انتظار بررسی'
        APPROVED = 'approved', 'تأیید شده'
        REJECTED = 'rejected', 'رد شده'
        DONE = 'done', 'انجام شده'

    order = models.ForeignKey(
        Order, on_delete=models.PROTECT, related_name='refund_requests'
    )
    payment = models.ForeignKey(
        Payment, on_delete=models.PROTECT, null=True, blank=True,
        related_name='refund_requests'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='refund_requests'
    )
    reason = models.TextField()

    refund_amount = models.DecimalField(
        max_digits=12, decimal_places=0, null=True, blank=True
    )
    
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    admin_note = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'RefundRequest #{self.pk} - {self.order.tracking_code}'







class DiscountCode(TimeStampedModel):
    class DiscountType(models.TextChoices):
        PERCENTAGE = 'percentage', 'درصدی'
        FIXED = 'fixed', 'مبلغ ثابت'

    code = models.CharField(max_length=30, unique=True, db_index=True)
    discount_type = models.CharField(max_length=10, choices=DiscountType.choices)

    # Percentage: 1–100. Fixed: amount in toman.
    value = models.DecimalField(max_digits=12, decimal_places=0)

    min_order_amount = models.DecimalField(
        max_digits=12, decimal_places=0, null=True, blank=True,
        help_text="حداقل مبلغ سبد برای اعمال این کد؛ خالی یعنی بدون محدودیت."
    )

    # Optional scope restrictions. Empty means the entire cart is eligible.
    categories = models.ManyToManyField('products.Category', blank=True, related_name='discount_codes')
    brands = models.ManyToManyField('products.Brand', blank=True, related_name='discount_codes')
    products = models.ManyToManyField('products.Product', blank=True, related_name='discount_codes')

    max_uses = models.PositiveIntegerField(
        null=True, blank=True, help_text="سقف کلی استفاده در کل سایت؛ خالی یعنی نامحدود."
    )
    max_uses_per_user = models.PositiveIntegerField(
        null=True, blank=True, help_text="سقف استفاده برای هر کاربر؛ خالی یعنی نامحدود."
    )

    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['code', 'is_active']),
        ]

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    @classmethod
    def generate_unique_code(cls, length=8):
        """Generate a unique random code."""
        alphabet = string.ascii_uppercase + string.digits
        while True:
            candidate = ''.join(secrets.choice(alphabet) for _ in range(length))
            if not cls.objects.filter(code=candidate).exists():
                return candidate

    @property
    def is_expired(self):
        if not self.valid_until:
            return False
        return timezone.now() > self.valid_until

    @property
    def is_not_started(self):
        return timezone.now() < self.valid_from

    @property
    def total_uses(self):
        return self.usages.filter(order__isnull=False).count()

    def uses_by_user(self, user):
        if not user or not user.is_authenticated:
            return 0
        return self.usages.filter(user=user, order__isnull=False).count()

    def has_scope_restriction(self):
        return self.categories.exists() or self.brands.exists() or self.products.exists()

    def applies_to_variant(self, variant):
        """Check whether this code applies to the given variant."""
        if not self.has_scope_restriction():
            return True
        product = variant.product
        if self.products.filter(pk=product.pk).exists():
            return True
        if product.category_id and self.categories.filter(pk=product.category_id).exists():
            return True
        if product.brand_id and self.brands.filter(pk=product.brand_id).exists():
            return True
        return False

    def validate_for_cart(self, cart, user):
        """
        Validate the discount code for a specific cart and user.
        Returns (True, None) or (False, 'error message').
        """
        if not self.is_active:
            return False, "این کد تخفیف غیرفعال است."
        if self.is_not_started:
            return False, "این کد تخفیف هنوز فعال نشده است."
        if self.is_expired:
            return False, "این کد تخفیف منقضی شده است."

        if self.max_uses is not None and self.total_uses >= self.max_uses:
            return False, "ظرفیت استفاده از این کد تخفیف تکمیل شده است."

        if self.max_uses_per_user is not None and self.uses_by_user(user) >= self.max_uses_per_user:
            return False, "شما قبلاً از سقف مجاز استفاده از این کد استفاده کرده‌اید."

        applicable_subtotal = self.get_applicable_subtotal(cart)
        if applicable_subtotal <= 0:
            return False, "این کد تخفیف روی هیچ‌کدام از کالاهای سبد شما قابل اعمال نیست."

        if self.min_order_amount is not None and applicable_subtotal < self.min_order_amount:
            return False, (
                f"حداقل مبلغ سفارش برای استفاده از این کد "
                f"{self.min_order_amount:,.0f} تومان است."
            )

        return True, None

    def get_applicable_subtotal(self, cart):
        """Calculate the subtotal of eligible cart items."""
        total = 0
        for item in cart.items.select_related('variant', 'variant__product'):
            if self.applies_to_variant(item.variant):
                total += item.unit_price * item.quantity
        return total

    def calculate_discount_amount(self, cart):
        """Calculate the discount for eligible items only."""
        applicable_subtotal = self.get_applicable_subtotal(cart)
        if applicable_subtotal <= 0:
            return 0

        if self.discount_type == self.DiscountType.PERCENTAGE:
            amount = applicable_subtotal * self.value / 100
        else:
            amount = self.value

        # The discount cannot exceed the eligible subtotal.
        return min(amount, applicable_subtotal)



class DiscountCodeUsage(TimeStampedModel):
    """
    Track each discount code usage for usage limits and historical snapshots.
    An order=None record means the code is reserved but the order is not finalized.
    """
    code = models.ForeignKey(DiscountCode, on_delete=models.PROTECT, related_name='usages')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='discount_usages')
    order = models.ForeignKey(
        'orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='discount_usages'
    )
    discount_amount = models.DecimalField(max_digits=12, decimal_places=0)

    class Meta:
        indexes = [
            models.Index(fields=['code', 'user']),
        ]

    def __str__(self):
        return f'{self.code.code} - {self.user.phone_number}'