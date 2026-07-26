from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.core.validators import RegexValidator

from django.utils import timezone
import random
from datetime import timedelta



phone_validator = RegexValidator(
    regex=r"^09\d{9}$",
    message="شماره موبایل باید با 09 شروع شود و 11 رقم باشد."
)


class UserManager(BaseUserManager):
    """
    creat a new user model base on phon number
    """

    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('شماره موبایل الزامی است')
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(phone_number, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(
        max_length=11, unique=True, validators=[phone_validator])
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    is_phone_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.phone_number



class OTPRequest(models.Model):

    """
    Stores OTP requests for phone-based authentication.
    Handles code generation, expiration, resend limitation, and verification attempts.
    """

    class Purpose(models.TextChoices):
        REGISTER_LOGIN = 'register_login', 'ثبت‌نام یا ورود'
        PASSWORD_RESET = 'password_reset', 'بازیابی رمز عبور'

    MAX_ATTEMPTS = 5
    CODE_LIFETIME_MINUTES = 2
    RESEND_COOLDOWN_SECONDS = 60

    phone_number = models.CharField(max_length=11, validators=[phone_validator])
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['phone_number', 'purpose', 'is_used'])]

    def __str__(self):
        """
        Returns a readable representation of the OTP request.
        """
        return f'{self.phone_number} - {self.get_purpose_display()}'

    @classmethod
    def generate(cls, phone_number, purpose):

        """
        Creates a new OTP request.
        Checks the resend cooldown period, generates a random six-digit code,
        and stores the OTP with an expiration time.
        """

        last = cls.objects.filter(
            phone_number=phone_number, purpose=purpose
        ).order_by('-created_at').first()

        if last and (timezone.now() - last.created_at).total_seconds() < cls.RESEND_COOLDOWN_SECONDS:
            raise ValueError('لطفاً کمی صبر کنید و دوباره تلاش کنید.')


        code = f'{random.randint(0, 999999):06d}'
        return cls.objects.create(
            phone_number=phone_number,
            code=code,
            purpose=purpose,
            expires_at=timezone.now() + timedelta(minutes=cls.CODE_LIFETIME_MINUTES),
        )

    @property
    def is_expired(self):

        """
        Checks whether the OTP code has passed its expiration time.
        """
        return timezone.now() > self.expires_at

    def verify(self, submitted_code):
        """
        Verifies a submitted OTP code.

        Checks whether the code is already used, expired, or exceeds
        the maximum number of attempts. Returns a success status and message.
        """
        if self.is_used:
            return False, 'این کد قبلاً استفاده شده است.'
        if self.is_expired:
            return False, 'کد منقضی شده است، دوباره درخواست بدهید.'
        if self.attempts >= self.MAX_ATTEMPTS:
            return False, 'تعداد تلاش مجاز تمام شده، دوباره درخواست بدهید.'

        self.attempts += 1
        if self.code != submitted_code:
            self.save(update_fields=['attempts'])
            return False, 'کد وارد شده نادرست است.'

        self.is_used = True
        self.save(update_fields=['attempts', 'is_used'])
        return True, None