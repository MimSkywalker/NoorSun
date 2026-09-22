import secrets

from django.core.mail import send_mail
from django.db import models
from django.urls import reverse
from django.utils import timezone

from core.models import TimeStampedModel


class SatisfactionSurvey(TimeStampedModel):
    order = models.OneToOneField(
        'orders.Order', on_delete=models.CASCADE, related_name='satisfaction_survey'
    )
    token = models.CharField(max_length=64, unique=True, editable=False)
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    comment = models.TextField(blank=True)
    is_submitted = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(null=True, blank=True)
    invitation_sent_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('notifications:survey_detail', kwargs={'token': self.token})

    def send_invitation(self):
        """
        ارسال پیامک/ایمیل حاوی لینک فرم نظرسنجی. Idempotent: اگر قبلاً
        دعوت ارسال شده یا کاربر قبلاً پاسخ داده، دوباره ارسال نمی‌کند —
        هم‌الگوی release_order_stock (فاز۵).
        """
        if self.invitation_sent_at or self.is_submitted:
            return

        from django.conf import settings
        from notifications.sms import get_sms_service

        url = f"{settings.SITE_BASE_URL}{self.get_absolute_url()}"
        message = f"لطفاً به خرید خود از ما امتیاز دهید: {url}"

        order = self.order
        if order.user_id:
            get_sms_service().send_message(order.user.phone_number, message)

            email = getattr(getattr(order.user, 'profile', None), 'email', None)
            if email:
                send_mail(
                    subject="نظرسنجی رضایت خرید",
                    message=message,
                    from_email=None,
                    recipient_list=[email],
                )

        self.invitation_sent_at = timezone.now()
        self.save(update_fields=['invitation_sent_at'])

    def __str__(self):
        return f'Survey for Order #{self.order_id}'