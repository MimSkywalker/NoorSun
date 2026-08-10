from decimal import Decimal


def get_discount_code(code_str):
    """Normalize and retrieve the discount code; return None if not found."""
    from .models import DiscountCode

    if not code_str:
        return None

    try:
        return DiscountCode.objects.get(code=code_str.strip().upper())
    except DiscountCode.DoesNotExist:
        return None


def apply_discount_code_to_cart(cart, code_str, user):
    """
    Validate and apply the discount code to the cart.
    Returns (True, None) on success or (False, error message) on failure.
    """
    code = get_discount_code(code_str)
    if code is None:
        return False, "کد تخفیف وارد شده معتبر نیست."

    ok, error = code.validate_for_cart(cart, user)
    if not ok:
        return False, error

    cart.discount_code = code
    cart.save(update_fields=['discount_code'])
    return True, None


def remove_discount_code_from_cart(cart):
    cart.discount_code = None
    cart.save(update_fields=['discount_code'])


def calculate_cart_discount(cart):
    """
    Return the current cart discount amount.
    Re-validates the code in case its conditions have changed.
    """
    if not cart.discount_code_id:
        return Decimal('0')

    code = cart.discount_code
    ok, _ = code.validate_for_cart(cart, cart.user)
    if not ok:
        return Decimal('0')

    return code.calculate_discount_amount(cart)