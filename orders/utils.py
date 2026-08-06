from .models import Cart, CartItem, Order, ProductVariant 
from django.db import transaction
from django.db.models import F



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
    Idempotently releases the stock reserved for an order, restores the
    corresponding sales_count, and updates the order status.

    This function only operates when the order is still in PENDING_PAYMENT
    status. If the order has already been processed, it returns False without
    making any changes.

    The row-level lock ensures that concurrent operations such as a successful
    PaymentCallbackView, manual cancellation, automatic expiration via a
    management command, or a lazy expiration check cannot process the same
    order simultaneously. Only one operation can successfully release the
    stock and change the status.
    """
    with transaction.atomic():
        try:
            order = Order.objects.select_for_update().get(pk=order_id)
        except Order.DoesNotExist:
            return False

        if order.status != Order.Status.PENDING_PAYMENT:
            return False  # The order has already been processed (successful, expired, or canceled).

                    stock=F('stock') + item.quantity
                )
                Product.objects.filter(pk=item.variant.product_id).update(
                    sales_count=F('sales_count') - item.quantity
                )

        order.status = new_status
        order.save(update_fields=['status', 'updated_at'])
        return True