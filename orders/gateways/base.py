from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class GatewayRequestResult:
    success: bool
    redirect_url: Optional[str] = None
    authority: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class GatewayVerifyResult:
    success: bool
    ref_id: Optional[str] = None
    error_message: Optional[str] = None
    raw_response: Optional[dict] = None


class PaymentGateway(ABC):
    """
    Common interface for all payment gateways.

    Each concrete gateway implementation (e.g. ZarinPal, IDPay, etc.)
    must inherit from this class and implement the two methods below.

    The rest of the application should never communicate directly with
    a specific gateway. All gateway-related operations must go through
    this interface so that gateway implementations remain interchangeable.
    """

    name: str = "base"

    @abstractmethod
    def request_payment(self, payment) -> GatewayRequestResult:
        """Initiate a payment request and return the authority and redirect URL."""
        raise NotImplementedError

    @abstractmethod
    def verify_payment(self, payment, callback_params: dict) -> GatewayVerifyResult:
        """Verify the payment transaction after the user returns from the gateway."""
        raise NotImplementedError