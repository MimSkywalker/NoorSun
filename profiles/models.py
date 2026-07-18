from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class Profile(TimeStampedModel):
    GENDER_CHOICES = [
        ('m', 'Male'),
        ('f', 'Female'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    wants_promotional_sms = models.BooleanField(default=True)

    def __str__(self):
        return f'profile | {self.user.phone_number}'