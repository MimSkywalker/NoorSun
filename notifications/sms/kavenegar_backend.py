import logging

from django.conf import settings

from .base import SMSBackend, OTPSMSBackend

logger = logging.getLogger(__name__)


class KavenegarSMSBackend(SMSBackend):

    """
    """
    name = "kavenegar"

    def send_message(self, phone_number, text) -> bool:
        from kavenegar import KavenegarAPI, APIException, HTTPException

        api_key = settings.KAVENEGAR_API_KEY
        sender = settings.KAVENEGAR_SENDER

        if not api_key:
            logger.error("KAVENEGAR_API_KEY تنظیم نشده؛ پیامک به %s ارسال نشد.", phone_number)
            return False

        try:
            api = KavenegarAPI(api_key)
            params = {
                'sender': sender,
                'receptor': phone_number,
                'message': text,
            }
            response = api.sms_send(params)
            logger.info("Kavenegar sms_send: پیامک به %s ارسال شد | پاسخ=%s", phone_number, response)
            return True
        except APIException as e:
            logger.error("Kavenegar APIException (sms_send) برای %s: %s", phone_number, e)
            return False
        except HTTPException as e:
            logger.error("Kavenegar HTTPException (sms_send) برای %s: %s", phone_number, e)
            return False
        except Exception:
            logger.exception("خطای پیش‌بینی‌نشده هنگام sms_send به %s", phone_number)
            return False


class KavenegarOTPBackend(OTPSMSBackend):
    """
    """

    name = "kavenegar"

    def send_otp(self, phone_number, code, template=None) -> bool:
        from kavenegar import KavenegarAPI, APIException, HTTPException

        api_key = settings.KAVENEGAR_API_KEY
        template_name = template or settings.KAVENEGAR_OTP_TEMPLATE

        if not api_key:
            logger.error("KAVENEGAR_API_KEY تنظیم نشده؛ OTP به %s ارسال نشد.", phone_number)
            return False
        if not template_name:
            logger.error(
                "KAVENEGAR_OTP_TEMPLATE تنظیم نشده (الگوی Verify هنوز در پنل "
                "ساخته/تأیید نشده)؛ OTP به %s ارسال نشد.", phone_number
            )
            return False

        try:
            api = KavenegarAPI(api_key)
            params = {
                'receptor': phone_number,
                'template': template_name,
                'token': str(code),
                'type': 'sms',
            }
            response = api.verify_lookup(params)
            logger.info("Kavenegar verify_lookup: OTP به %s ارسال شد | پاسخ=%s", phone_number, response)
            return True
        except APIException as e:
            logger.error("Kavenegar APIException (verify_lookup) برای %s: %s", phone_number, e)
            return False
        except HTTPException as e:
            logger.error("Kavenegar HTTPException (verify_lookup) برای %s: %s", phone_number, e)
            return False
        except Exception:
            logger.exception("خطای پیش‌بینی‌نشده هنگام verify_lookup به %s", phone_number)
            return False