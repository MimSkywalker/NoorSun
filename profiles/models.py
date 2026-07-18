import io
import random

from PIL import Image

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import FileExtensionValidator
from django.db import models

from core.models import TimeStampedModel
from datetime import date


def validate_birth_date(value):
    if value > date.today():
        raise ValidationError("نمی‌توانید در آینده متولد شده باشید!")
    age = (date.today() - value).days // 365
    if age > 120:
        raise ValidationError("تاریخ تولد معتبر نیست.")


def random_default_avatar():
    avatars = [f"avatars/defaults/avatar{i}.webp" for i in range(1, 11)]
    return random.choice(avatars)


def user_avatar_path(instance, filename):
    return f"avatars/users/{instance.user_id}/avatar.webp"


def validate_image_size(image):
    max_size = 5 * 1024 * 1024
    if image.size > max_size:
        raise ValidationError("حجم تصویر باید کمتر از ۵ مگابایت باشد.")


def validate_image_dimensions(image):
    with Image.open(image) as img:
        width, height = img.size
    if width > 4000 or height > 4000:
        raise ValidationError("ابعاد تصویر بیش از حد بزرگ است.")


def convert_to_webp(image_field, max_size=(512, 512), quality=80):
    """
    Convert an uploaded image to WebP format, resize it while preserving
    its aspect ratio, and return it as a Django ContentFile.
    """
    with Image.open(image_field) as img:

        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGBA')
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        else:
            img = img.convert('RGB')

        img.thumbnail(max_size, Image.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer,
                 format='WEBP',
                 quality=quality,
                 optimize=True,
                 method=6,)
        buffer.seek(0)

    return ContentFile(buffer.read(), name='avatar.webp')


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
    avatar = models.ImageField(upload_to=user_avatar_path, blank=True, null=True, default=random_default_avatar,  validators=[
        validate_image_size,
        validate_image_dimensions,
        FileExtensionValidator(allowed_extensions=[
                               "jpg", "jpeg", "png", "webp"]),
    ],)
    email = models.EmailField(blank=True, null=True)
    birth_date = models.DateField(
        null=True, blank=True,  validators=[validate_birth_date])
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    wants_promotional_sms = models.BooleanField(default=True)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f'profile | {self.user.phone_number}'

    def save(self, *args, **kwargs):
        old_avatar = None
        avatar_changed = self.pk is None

        if self.pk:
            try:
                old_profile = Profile.objects.get(pk=self.pk)
                old_avatar = old_profile.avatar
                avatar_changed = old_avatar != self.avatar
            except Profile.DoesNotExist:
                pass

        if avatar_changed and self.avatar and 'defaults' not in self.avatar.name:
            converted = convert_to_webp(self.avatar)
            self.avatar = converted

        if avatar_changed and old_avatar and 'defaults' not in old_avatar.name:
            old_avatar.delete(save=False)

        if self.email and self.gender and self.birth_date:
            self.is_completed = True
        else:
            self.is_completed = False

        super().save(*args, **kwargs)
