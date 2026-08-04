from .models import Cart, CartItem


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


def merge_guest_cart_into_user(request, user):
    """
    Merge a guest cart into the authenticated user's cart.

    If both carts contain the same product variant, their quantities
    are combined without exceeding the available stock. Otherwise,
    guest items are transferred to the user's cart. The guest cart is
    removed after the merge is complete.
    """

    # Get current guest session
    session_key = request.session.session_key
    if not session_key:
        return

    try:
        guest_cart = Cart.objects.get(session_key=session_key, user=None, is_active=True)
    except Cart.DoesNotExist:
        return

    user_cart, _ = Cart.objects.get_or_create(user=user, is_active=True)


# Move each guest item
    for item in guest_cart.items.all():
        # Check if variant already exists
        existing = user_cart.items.filter(variant=item.variant).first()
        # Merge quantities
        if existing:
            new_qty = existing.quantity + item.quantity

            # Do not exceed available stock
            existing.quantity = min(new_qty, item.variant.stock)
            existing.save(update_fields=['quantity'])
            item.delete()
        else:
            # Move item to user's cart
            item.cart = user_cart
            item.save(update_fields=['cart'])

    guest_cart.delete()