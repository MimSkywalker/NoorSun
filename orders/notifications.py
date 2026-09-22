import logging

from django.core.mail import send_mail

from notifications.sms import get_sms_service
from notifications.models import SatisfactionSurvey

logger = logging.getLogger(__name__)


def _order_contact_phone(order):
    return order.user.phone_number if order.user_id else None


def _order_contact_email(order):
    if order.user_id and hasattr(order.user, 'profile'):
        return order.user.profile.email
    return None


def notify_order_shipped(order):
    message = f"سفارش شما با کد پیگیری {order.tracking_code} ارسال شد."
    _send_order_notification(order, message, subject="سفارش شما ارسال شد")


def notify_order_delivered(order):
    message = (
        f"سفارش شما با کد پیگیری {order.tracking_code} تحویل داده شد. "
        f"از خرید شما سپاسگزاریم."
    )
    _send_order_notification(order, message, subject="سفارش شما تحویل داده شد")

    survey, _created = SatisfactionSurvey.objects.get_or_create(order=order)
    survey.send_invitation()


def _send_order_notification(order, message, subject):
    phone = _order_contact_phone(order)
    email = _order_contact_email(order)

    if phone:
        get_sms_service().send_message(phone, message)

    if email:
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=None,
                recipient_list=[email],
            )
        except Exception:
            logger.exception("خطا هنگام ارسال ایمیل اطلاع‌رسانی سفارش #%s", order.pk)