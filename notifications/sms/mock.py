import logging

from .base import SMSBackend, OTPSMSBackend

logger = logging.getLogger(__name__)


class MockSMSBackend(SMSBackend, OTPSMSBackend):
    """
    """

    name = "mock"

    def send_message(self, phone_number, text) -> bool:
        logger.info("SMS to %s: %s", phone_number, text)
        print(f"[MockSMS] to {phone_number}: {text}")
        return True

    def send_otp(self, phone_number, code, template=None) -> bool:
        logger.info("Mock OTP to %s: code=%s template=%s", phone_number, code, template)
        print(f"[MockOTP] to {phone_number}: code={code}")
        return True