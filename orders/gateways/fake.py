import uuid

from django.urls import reverse

from .base import PaymentGateway, GatewayRequestResult, GatewayVerifyResult


class FakePaymentGateway(PaymentGateway):
    """
    A simulated payment gateway for development and testing.

    This gateway does not communicate with any external payment provider.
    Instead of redirecting the user to a real payment gateway, it redirects
    the user to an internal FakeGatewayView where the payment result can be
    manually simulated as either successful or unsuccessful.

    This allows the complete payment flow to be tested:

        Request Payment → Redirect → Callback → Verify

    without requiring real gateway credentials, external network requests,
    or actual payments.
    """

    # The identifier used by the application to select this gateway.
    name = "fake"

    def request_payment(self, payment) -> GatewayRequestResult:
        """
        Create a simulated payment request.

        A unique fake authority is generated for the payment, and the user
        is redirected to the internal fake gateway page.
        """

        # Generate a unique identifier that represents the gateway authority.
        authority = f"FAKE-{uuid.uuid4().hex[:16]}"

        # Build the URL of the internal fake gateway page.
        # This simulates the redirect to a real external payment gateway.
        redirect_url = reverse("orders:fake_gateway", args=[payment.pk])

        return GatewayRequestResult(
            success=True,
            redirect_url=redirect_url,
            authority=authority,
        )

    def verify_payment(self, payment, callback_params: dict) -> GatewayVerifyResult:
        """
        Verify the simulated payment result.

        The fake gateway reads the payment result from the callback parameters
        instead of making a request to an external payment provider.
        """

        # Read the simulated result sent back by the fake gateway page.
        result = callback_params.get("result")

        if result == "success":
            # Generate a fake reference ID to simulate the identifier
            # normally returned by a real payment gateway after verification.
            return GatewayVerifyResult(
                success=True,
                ref_id=f"REF-{uuid.uuid4().hex[:12]}",
                raw_response=callback_params,
            )

        # Any result other than "success" is treated as a failed/CANCELLED payment.
        return GatewayVerifyResult(
            success=False,
            error_message="Payment was canceled by the user or failed (simulated).",
            raw_response=callback_params,
        )
