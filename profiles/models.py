import io
import random

from PIL import Image
import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import FileExtensionValidator
from django.db import models

from core.models import TimeStampedModel
import secrets

from datetime import date, timedelta
from django.utils import timezone


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
    return f"avatars/users/{instance.user_id}/avatar_{uuid.uuid4().hex[:8]}.webp"


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
    email = models.EmailField(blank=True, null=True, unique=True)
    is_email_verified = models.BooleanField(default=False)
    birth_date = models.DateField(
        null=True, blank=True,  validators=[validate_birth_date])
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    wants_promotional_sms = models.BooleanField(default=True)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f'profile | {self.user.phone_number}'

    def save(self, *args, verified_email_change=False, **kwargs):
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
            try:
                old_avatar.delete(save=False)
            except (PermissionError, OSError):
                pass


        if self.pk and not verified_email_change:
            old_email = Profile.objects.filter(
                pk=self.pk).values_list('email', flat=True).first()
            if old_email != self.email:
                self.is_email_verified = False

        if self.email and self.gender and self.birth_date and self.is_email_verified:
            self.is_completed = True
        else:
            self.is_completed = False

        super().save(*args, **kwargs)


class EmailVerification(TimeStampedModel):

    # Maximum number of verification attempts
    MAX_ATTEMPTS = 5

    # Cooldown before requesting another code
    RESEND_COOLDOWN_SECONDS = 60

    # Verification code lifetime
    CODE_LIFETIME_MINUTES = 15

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='email_verifications',
    )
    email = models.EmailField()
    code = models.CharField(max_length=6)
    attempts = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.email} - {self.user.phone_number}'

    @classmethod
    def generate(cls, user, email):
        # Prevent requesting a new code too quickly
        last = (
            cls.objects
            .filter(user=user, email=email)
            .order_by('-created_at')
            .first()
        )

        if (
            last
            and (timezone.now() - last.created_at).total_seconds()
            < cls.RESEND_COOLDOWN_SECONDS
        ):
            raise ValueError('لطفاً کمی صبر کنید و دوباره تلاش کنید.')

        code = f'{secrets.randbelow(1000000):06d}'

        return cls.objects.create(
            user=user,
            email=email,
            code=code,
            expires_at=timezone.now() + timedelta(
                minutes=cls.CODE_LIFETIME_MINUTES
            ),
        )

    @property
    def is_expired(self):
        """Return True if the verification code has expired."""
        return timezone.now() > self.expires_at

    def verify(self, submitted_code):
        # Reject already used codes
        if self.is_used:
            return False, 'این کد قبلاً استفاده شده است.'

        # Reject expired codes
        if self.is_expired:
            return False, 'کد منقضی شده، دوباره درخواست بدهید.'

        # Stop verification after too many failed attempts
        if self.attempts >= self.MAX_ATTEMPTS:
            return False, 'تعداد تلاش مجاز تمام شده. دوباره درخواست دهید.'

        # Count this verification attempt
        self.attempts += 1

        # Invalid verification code
        if self.code != submitted_code:
            self.save(update_fields=['attempts'])
            return False, 'کد وارد شده نادرست است.'

        # Mark the code as used
        self.is_used = True
        self.save(update_fields=['attempts', 'is_used'])

        profile = self.user.profile
        profile.email = self.email
        profile.is_email_verified = True
        profile.save(verified_email_change=True)

        return True, None
