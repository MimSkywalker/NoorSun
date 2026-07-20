from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils.text import slugify

from core.models import TimeStampedModel

postal_code_validator = RegexValidator(
    regex=r'^\d{10}$',
    message='کد پستی باید دقیقاً ۱۰ رقم باشد.'
)

receiver_phone_validator = RegexValidator(
    regex=r'^09\d{9}$',
    message='شماره موبایل گیرنده باید با 09 شروع شود و 11 رقم باشد.'
)


class Province(models.Model):
    title = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)


class City(models.Model):
    province = models.ForeignKey(Province, on_delete=models.PROTECT, related_name='cities')
    title = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, blank=True)

    class Meta:
        ordering = ['title']
        unique_together = ('province', 'title')

    def __str__(self):
        return f'{self.title} ({self.province.title})'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)


class Address(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='addresses'
    )
    title = models.CharField(max_length=50, help_text='مثلاً خانه، محل کار')
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name='addresses')
    full_address = models.TextField()
    postal_code = models.CharField(max_length=10, validators=[postal_code_validator])
    receiver_name = models.CharField(max_length=150)
    receiver_phone = models.CharField(max_length=11, validators=[receiver_phone_validator])
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_default', '-created_at']
        verbose_name_plural = 'addresses'

    def __str__(self):
        return f'{self.title} - {self.user.phone_number}'

    def save(self, *args, **kwargs):
        is_first_address = self.pk is None and not Address.objects.filter(user=self.user).exists()
        if is_first_address:
            self.is_default = True  # اولین آدرس هر کاربر خودکار پیش‌فرض می‌شود

        super().save(*args, **kwargs)

        if self.is_default:
            Address.objects.filter(user=self.user).exclude(pk=self.pk).update(is_default=False)