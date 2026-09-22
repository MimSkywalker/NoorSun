# import logging

# logger = logging.getLogger(__name__)


# class MockSMSService:
#     """
#     Mock version of the SMS service.
#     Currently, it only prints the code to the log/console.
#     In later phases, this class will be replaced or combined
#     with a real implementation (for example, Kavenegar),
#     without changing the calling code,
#     because the signature of the send_otp method remains the same.
#     """

#     def send_otp(self, phone_number: str, code: str):
#         logger.info(f"[MockSMS] به {phone_number} کد {code} ارسال شد.")
#         print(f"[MockSMS] کد ورود برای {phone_number}: {code}")


#     def send_message(self, phone_number, text):
#         logger.info("SMS to %s: %s", phone_number, text)
#         print(f"[MockSMS] to {phone_number}: {text}")


#         return True

# sms_service = MockSMSService()




"""
⚠️ منسوخ شده از فاز۸.

منطق واقعی سرویس پیامک به notifications/sms منتقل شده (معماری مستقل از
Provider، هم‌الگوی orders/gateways فاز۵). این فایل فقط برای سازگاری با
importهای قدیمی نگه داشته شده. در کدهای جدید از این استفاده کنید:

    from notifications.sms import get_sms_service
    sms_service = get_sms_service()
"""
from notifications.sms.mock import MockSMSBackend as MockSMSService  # noqa: F401


