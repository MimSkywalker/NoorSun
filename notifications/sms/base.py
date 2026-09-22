from abc import ABC, abstractmethod


class SMSBackend(ABC):
    """
    Interface for regular SMS messages such as notifications,
    promotions, order updates, and stock alerts.
    Uses sms_send with custom text.
    """

    name: str = "base"

    @abstractmethod
    def send_message(self, phone_number, text) -> bool:
        """Send a custom text message. True if successful."""
        raise NotImplementedError


class OTPSMSBackend(ABC):
    """
    Separate interface for OTP/verification SMS.
    Uses the Verify/Lookup service with a pre-approved template,
    rather than sms_send.
    """

    name: str = "base"

    @abstractmethod
    def send_otp(self, phone_number, code, template=None) -> bool:
        """
        Send an OTP code. Optionally override the template;
        otherwise use settings.KAVENEGAR_OTP_TEMPLATE.
        """
        raise NotImplementedError
