import logging

logger = logging.getLogger(__name__)


class MockSMSService:
    """
    نسخه‌ی Mock سرویس پیامک. فعلاً فقط کد رو در لاگ/کنسول چاپ می‌کنه.
    در فاز‌های بعدی، این کلاس با یک پیاده‌سازی واقعی (مثلاً کاوه‌نگار)
    جایگزین یا ترکیب می‌شه — بدون این‌که کد صداکننده‌اش تغییر کنه،
    چون امضای متد send_otp ثابت می‌مونه.

    ---------------------------------------

    Mock version of the SMS service.
    Currently, it only prints the code to the log/console.
    In later phases, this class will be replaced or combined
    with a real implementation (for example, Kavenegar),
    without changing the calling code,
    because the signature of the send_otp method remains the same.
    """

    def send_otp(self, phone_number: str, code: str):
        logger.info(f"[MockSMS] به {phone_number} کد {code} ارسال شد.")
        print(f"[MockSMS] کد ورود برای {phone_number}: {code}")
        return True


sms_service = MockSMSService()