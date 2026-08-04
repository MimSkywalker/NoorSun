from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.models import TimeStampedModel
from products.models import ProductVariant


import random
import string
from datetime import date

from django.db import transaction


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
