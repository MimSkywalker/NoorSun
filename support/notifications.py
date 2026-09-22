import logging

from django.core.mail import send_mail

from notifications.sms import get_sms_service

logger = logging.getLogger(__name__)


def notify_ticket_replied(ticket):
    """

    """
    message = f"به تیکت شما با موضوع «{ticket.subject}» پاسخ داده شد."

    if ticket.user_id:
        phone = ticket.user.phone_number
        email = getattr(getattr(ticket.user, 'profile', None), 'email', None)
    else:
        phone = ticket.guest_phone
        email = ticket.guest_email

    if phone:
        get_sms_service().send_message(phone, message)

    if email:
        try:
            send_mail(
                subject="پاسخ به تیکت پشتیبانی شما",
                message=message,
                from_email=None,
                recipient_list=[email],
            )
        except Exception:
            logger.exception("خطا هنگام ارسال ایمیل پاسخ تیکت #%s", ticket.pk)