from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel
from users.models import phone_validator


class Ticket(TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = 'open', 'باز'
        ANSWERED = 'answered', 'پاسخ داده‌شده'
        CLOSED = 'closed', 'بسته‌شده'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='tickets',
    )
    guest_name = models.CharField(max_length=100, blank=True)
    guest_phone = models.CharField(
        max_length=11, blank=True, validators=[phone_validator]
    )
    guest_email = models.EmailField(blank=True)
    subject = models.CharField(max_length=255)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.OPEN
    )

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['user', 'status']),
        ]

    def clean(self):
        if not self.user_id and not (self.guest_phone or self.guest_email):
            raise ValidationError(
                "برای تیکت مهمان، حداقل شماره موبایل یا ایمیل باید وارد شود."
            )

    @property
    def contact_display(self):
        if self.user_id:
            return self.user.phone_number
        return self.guest_phone or self.guest_email or '—'

    def __str__(self):
        return f'Ticket #{self.pk} - {self.subject} ({self.get_status_display()})'


class TicketMessage(models.Model):
    class SenderType(models.TextChoices):
        USER = 'user', 'کاربر'
        ADMIN = 'admin', 'پشتیبانی'

    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name='messages'
    )
    sender_type = models.CharField(max_length=10, choices=SenderType.choices)
    sender_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ticket_messages',
        help_text="فرستنده‌ی واقعی پیام (کاربر یا ادمین). برای پیام مهمان خالی می‌ماند.",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def save(self, *args, **kwargs):
        """

        """
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            if self.sender_type == self.SenderType.ADMIN:
                Ticket.objects.filter(
                    pk=self.ticket_id
                ).exclude(status=Ticket.Status.CLOSED).update(
                    status=Ticket.Status.ANSWERED, updated_at=timezone.now()
                )
                from .notifications import notify_ticket_replied
                notify_ticket_replied(self.ticket)
            elif self.sender_type == self.SenderType.USER:
                Ticket.objects.filter(pk=self.ticket_id).update(
                    status=Ticket.Status.OPEN, updated_at=timezone.now()
                )

    def __str__(self):
        return f'Message #{self.pk} on Ticket #{self.ticket_id} ({self.get_sender_type_display()})'


class FAQ(TimeStampedModel):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.PositiveIntegerField(
        default=0, help_text="عدد کوچک‌تر، بالاتر نمایش داده می‌شود."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = 'سؤال متداول'
        verbose_name_plural = 'سؤالات متداول'

    def __str__(self):
        return self.question
