from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .mock import MockSMSBackend
from .kavenegar_backend import KavenegarSMSBackend, KavenegarOTPBackend

SMS_BACKEND_REGISTRY = {
    'mock': MockSMSBackend,
    'kavenegar': KavenegarSMSBackend,
}

OTP_BACKEND_REGISTRY = {
    'mock': MockSMSBackend,
    'kavenegar': KavenegarOTPBackend,
}


def get_sms_service():
    """
    """
    backend_name = getattr(settings, 'SMS_BACKEND', 'mock')
    backend_class = SMS_BACKEND_REGISTRY.get(backend_name)
    if backend_class is None:
        raise ImproperlyConfigured(f"سرویس پیامک '{backend_name}' ثبت نشده است.")
    return backend_class()


def get_otp_service():
    """
    """
    backend_name = getattr(settings, 'SMS_OTP_BACKEND', 'mock')
    backend_class = OTP_BACKEND_REGISTRY.get(backend_name)
    if backend_class is None:
        raise ImproperlyConfigured(f"سرویس OTP '{backend_name}' ثبت نشده است.")
    return backend_class()