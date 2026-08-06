from django.db import transaction
from django.db.models import F, Value
import logging

from .models import Cart, CartItem, Order, ProductVariant
from products.models import Product
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.db.models.functions import Greatest

logger = logging.getLogger(__name__)

def get_or_create_cart(request):
    """
      Return the active shopping cart for the current request.

    - Authenticated users get a cart linked to their account.
    - Guests get a cart linked to their session.
    - A new cart is created automatically if none exists.
    """
    if request.user.is_authenticated:
        # Get active cart or create one
        cart, _ = Cart.objects.get_or_create(user=request.user, is_active=True)
        return cart

    # Create a session for guest
    if not request.session.session_key:

        request.session.create()
    session_key = request.session.session_key

    # Get or create guest cart
    cart, _ = Cart.objects.get_or_create(
        session_key=session_key, user=None, is_active=True
    )
    return cart


def merge_guest_cart_into_user(request, user, guest_session_key=None):
    """
    Merge the guest cart created before authentication into the user's cart.

    The guest cart is identified by the session key that was associated with
    the guest session before login. Since Django may rotate the session key
    during login, the original guest session key should be captured before
    calling login() and passed to this function explicitly.

    If both carts contain the same product variant, their quantities are
    combined without exceeding the variant's available stock. If the variant
    exists only in the guest cart, the item is transferred to the user's cart.
    The guest cart is deleted after all of its items have been processed.
    """

    # Use the session key captured before login when available.
    # This is important because the session key may change during authentication.
    session_key = guest_session_key or request.session.session_key

    # There is no guest cart to merge if no session key is available.
    if not session_key:
        return

    try:
        # Retrieve the active guest cart associated with the previous session.
        guest_cart = Cart.objects.get(
            session_key=session_key,
            user=None,
            is_active=True
        )
    except Cart.DoesNotExist:
        # Nothing needs to be merged if no matching guest cart exists.
        return

    # Retrieve the user's active cart or create one if it does not exist.
    user_cart, _ = Cart.objects.get_or_create(
        user=user,
        is_active=True
    )

    # Process each item currently stored in the guest cart.
    for item in guest_cart.items.all():
        # Check whether the same product variant already exists
        # in the authenticated user's cart.
        existing = user_cart.items.filter(variant=item.variant).first()

        if existing:
            # Combine the quantities from the guest and user carts.
            new_qty = existing.quantity + item.quantity

            # Ensure that the merged quantity does not exceed
            # the currently available stock for the variant.
            existing.quantity = min(new_qty, item.variant.stock)

            # Update only the quantity field in the database.
            existing.save(update_fields=['quantity'])

            # Remove the guest-cart item because its quantity
            # has already been merged into the user's cart.
            item.delete()

        else:
            # Transfer the guest-cart item to the user's cart
            # when the same variant does not already exist there.
            item.cart = user_cart

            # Update only the cart relationship in the database.
            item.save(update_fields=['cart'])

    # Remove the guest cart after all of its items have been merged.
    guest_cart.delete()


def release_order_stock(order_id, new_status):
    """
    Release the stock reserved for a pending order and update its status.

    The operation is idempotent:
    - Only orders that are still PENDING_PAYMENT are processed.
    - select_for_update() prevents concurrent operations from processing
      the same order at the same time.
    - sales_count is clamped to zero to prevent database constraint errors.
    """
    with transaction.atomic():
        try:
            # Lock the order row to prevent concurrent processes from handling
            # the same pending order at the same time.
            order = Order.objects.select_for_update().get(pk=order_id)
        except Order.DoesNotExist:
            return False

        # Only PENDING_PAYMENT orders can release their reserved stock.
        # This also makes the operation idempotent.
        if order.status != Order.Status.PENDING:
            return False

        # Load the order items together with their variant and product
        # to avoid unnecessary database queries.
        for item in order.items.select_related('variant', 'product'):
            if item.variant_id:
                # Restore the quantity reserved by this order back to the variant stock.
                ProductVariant.objects.filter(pk=item.variant_id).update(
                    stock=F('stock') + item.quantity
                )

            # Use the product snapshot stored on OrderItem instead of
            # the live variant.product relationship.
            product_id = item.product_id

            # Old OrderItems may not have a product snapshot.
            # In that case, log the issue and skip sales_count restoration.
            if product_id is None:
                logger.warning(
                    "release_order_stock: آیتم #%s سفارش %s فاقد Snapshot "
                    "محصول است؛ sales_count برای این آیتم بازگردانده نشد.",
                    item.pk, order_id,
                )
                continue

            # Decrease sales_count using the product snapshot.
            # Greatest(..., 0) prevents the value from becoming negative.
            Product.objects.filter(pk=product_id).update(
                sales_count=Greatest(F('sales_count') - item.quantity, Value(0))
            )

            # Check whether sales_count was clamped to zero.
            current = Product.objects.filter(
                pk=product_id
            ).values_list(
                'sales_count', flat=True
            ).first()

            if current == 0:
                logger.warning(
                    "release_order_stock: sales_count محصول %s هنگام آزادسازی "
                    "سفارش %s (تعداد آیتم=%s) به صفر چسبید؛ احتمال ناهم‌خوانی داده "
                    "— بررسی شود.",
                    product_id, order_id, item.quantity,
                )

        # Update the order status only after all stock operations succeed.
        order.status = new_status
        order.save(update_fields=['status', 'updated_at'])

        return True


def check_and_expire_order(order):
    """
    Lazily expire an unpaid order after the configured payment timeout.

    Uses the idempotent stock-release function, making repeated calls safe.
    """
    # Only pending payments can expire.
    if order.status != Order.Status.PENDING:
        return order

    # Check whether the payment window has expired.
    timeout = timedelta(minutes=settings.ORDER_PAYMENT_TIMEOUT_MINUTES)
    if timezone.now() - order.created_at > timeout:
        release_order_stock(order.pk, Order.Status.EXPIRED)

        # Reload the order to reflect the updated status.
        order.refresh_from_db()

    return order



