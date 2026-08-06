from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .fake import FakePaymentGateway
# Later: from .zarinpal import ZarinPalGateway


# Registry of all available payment gateway implementations.
# The key is the gateway name stored/used by the application,
# and the value is the corresponding gateway class.
GATEWAY_REGISTRY = {
    "fake": FakePaymentGateway,
    # "zarinpal": ZarinPalGateway,
}


def get_gateway(name: str = None):
    """
    Return an instance of the requested payment gateway.

    If a gateway name is explicitly provided, it is used directly.
    This is important during the callback flow because the payment
    must be verified using the same gateway that originally created it.

    If no name is provided, the active gateway is read from
    settings.PAYMENT_GATEWAY. This is typically used when starting
    a new payment.

    Raises ImproperlyConfigured if the requested gateway is not
    registered in GATEWAY_REGISTRY.
    """
    # Use the explicitly provided gateway name when available.
    # Otherwise, fall back to the globally configured active gateway.
    gateway_name = name or settings.PAYMENT_GATEWAY

    # Look up the corresponding gateway class in the registry.
    gateway_class = GATEWAY_REGISTRY.get(gateway_name)

    if gateway_class is None:
        raise ImproperlyConfigured(
            f"Payment gateway '{gateway_name}' is not registered."
        )

    # Instantiate and return the gateway implementation.
    return gateway_class()
