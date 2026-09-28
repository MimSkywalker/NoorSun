import io

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.text import Truncator
from django_ckeditor_5.fields import CKEditor5Field

from core.images import crop_to_webp
from core.models import TimeStampedModel
from core.slugs import generate_unique_slug
from products.validators import validate_image_extension, validate_image_size

from .utils import slide_desktop_upload_path, slide_mobile_upload_path, link_validator
from .template_utils import is_valid_custom_template

# ---------------------------------------------------------------- slider




class SlideQuerySet(models.QuerySet):
    def visible(self):
        """ """
        now = timezone.now()
        return (
            self.filter(is_active=True)
            .filter(Q(start_at__isnull=True) | Q(start_at__lte=now))
            .filter(Q(end_at__isnull=True) | Q(end_at__gte=now))
        )


class Slide(TimeStampedModel):
    title = models.CharField('عنوان', max_length=150, blank=True)
    subtitle = models.CharField('زیرعنوان', max_length=255, blank=True)
    button_text = models.CharField('متن دکمه', max_length=50, blank=True)
    link_url = models.CharField(
        'لینک', max_length=500, blank=True, validators=[link_validator],
        help_text="مثال: /products/ یا https://example.com — اگر خالی باشد اسلاید لینک ندارد.",
    )

    image = models.ImageField(
        'تصویر دسکتاپ', upload_to=slide_desktop_upload_path,
        validators=[validate_image_size, validate_image_extension],
        help_text="به‌صورت خودکار به اندازه‌ی SLIDER_DESKTOP_SIZE (پیش‌فرض ۱۹۲۰×۷۰۰) کراپ می‌شود.",
    )
    image_mobile = models.ImageField(
        'تصویر موبایل', upload_to=slide_mobile_upload_path, blank=True, null=True,
        validators=[validate_image_size, validate_image_extension],
        help_text="اختیاری؛ به اندازه‌ی SLIDER_MOBILE_SIZE (پیش‌فرض ۸۰۰×۸۰۰) کراپ می‌شود. اگر خالی باشد، تصویر دسکتاپ استفاده می‌شود.",
    )
    image_alt = models.CharField('متن جایگزین تصویر (alt)', max_length=200, blank=True)

    order = models.PositiveIntegerField('ترتیب', default=0, help_text="عدد کوچک‌تر، زودتر نمایش داده می‌شود.")
    is_active = models.BooleanField('فعال', default=True)
    start_at = models.DateTimeField('شروع نمایش', null=True, blank=True, help_text="خالی = از همین حالا")
    end_at = models.DateTimeField('پایان نمایش', null=True, blank=True, help_text="خالی = بدون پایان")

    objects = SlideQuerySet.as_manager()

    class Meta:
        verbose_name = 'اسلاید'
        verbose_name_plural = 'اسلایدهای صفحه اصلی'
        ordering = ['order', '-created_at']
        indexes = [models.Index(fields=['is_active', 'start_at', 'end_at'])]

    def clean(self):
        if self.start_at and self.end_at and self.start_at >= self.end_at:
            raise ValidationError("زمان شروع باید قبل از زمان پایان باشد.")
        if self.button_text and not self.link_url:
            raise ValidationError("برای نمایش دکمه، وارد کردن لینک الزامی است.")

    @property
    def is_visible_now(self):
        now = timezone.now()
        return (
            self.is_active
            and (self.start_at is None or self.start_at <= now)
            and (self.end_at is None or self.end_at >= now)
        )

    @property
    def mobile_image_or_desktop(self):
        return self.image_mobile if self.image_mobile else self.image

    def _crop_field_if_new(self, field_file, size):
        # _committed=False یعنی فایل تازه آپلود شده و هنوز روی storage ذخیره نشده
        if field_file and not field_file._committed:
            field_file.seek(0)
            raw = field_file.read()
            content = crop_to_webp(io.BytesIO(raw), size)
            field_file.save(content.name, content, save=False)

    def save(self, *args, **kwargs):
        self._crop_field_if_new(self.image, tuple(settings.SLIDER_DESKTOP_SIZE))
        self._crop_field_if_new(self.image_mobile, tuple(settings.SLIDER_MOBILE_SIZE))
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title or f'Slide #{self.pk}'


# ------------------------------------------------------------ Static Pages

class StaticPage(TimeStampedModel):
    title = models.CharField('عنوان', max_length=200)
    title_en = models.CharField(
        'عنوان انگلیسی', max_length=200, blank=True,
        help_text="اگر اسلاگ را خالی بگذارید، از روی همین ساخته می‌شود.",
    )
    slug = models.SlugField(
        'اسلاگ', max_length=150, unique=True, blank=True, allow_unicode=False,
        help_text="فقط حروف انگلیسی، عدد و خط تیره. خالی بگذارید تا از عنوان انگلیسی ساخته شود. "
                  "تغییر بعد از انتشار، لینک قبلی صفحه را از کار می‌اندازد.",
    )
    content = CKEditor5Field(
        'محتوا', config_name='default', blank=True,
        help_text="برای صفحه‌ی قالب‌دار اختیاری است؛ برای قالب پیش‌فرض الزامی است.",
    )
    template_name = models.CharField(
        'قالب اختصاصی', max_length=150, blank=True,
        help_text="خالی = قالب پیش‌فرض. قالب‌های اختصاصی از پوشه‌ی templates/pages/custom/ خوانده می‌شوند.",
    )

    is_active = models.BooleanField('فعال', default=True)
    show_in_menu = models.BooleanField('نمایش در منو', default=False)
    show_in_footer = models.BooleanField('نمایش در فوتر', default=True)
    order = models.PositiveIntegerField('ترتیب', default=0)

    meta_title = models.CharField('عنوان سئو', max_length=70, blank=True)
    meta_description = models.CharField(
        'توضیحات سئو', max_length=160, blank=True,
        help_text="اگر خالی بماند، خودکار از ابتدای محتوا ساخته می‌شود.",
    )
    include_in_sitemap = models.BooleanField('عضویت در sitemap', default=True)

    class Meta:
        verbose_name = 'صفحه ثابت'
        verbose_name_plural = 'صفحات ثابت'
        ordering = ['order', 'id']

    def clean(self):
        if not self.slug and not (self.title_en or '').strip():
            raise ValidationError(
                "یکی از دو فیلد «اسلاگ» یا «عنوان انگلیسی» را پر کنید "
                "(آدرس صفحه باید لاتین باشد)."
            )
        if self.template_name and not is_valid_custom_template(self.template_name):
            raise ValidationError({
                'template_name': "این قالب در پوشه‌ی templates/pages/custom/ پیدا نشد."
            })
        if not self.template_name and not (self.content or '').strip():
            raise ValidationError({
                'content': "برای صفحه‌ی بدون قالب اختصاصی، محتوا الزامی است."
            })

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(
                type(self), (self.title_en or '').strip(), self.pk, allow_unicode=False
            )
        if not self.meta_description:
            plain = strip_tags(self.content or '')
            self.meta_description = Truncator(plain).words(25)[:160]
        super().save(*args, **kwargs)

    @property
    def effective_meta_title(self):
        return self.meta_title or self.title

    def get_absolute_url(self):
        return reverse('pages:detail', kwargs={'slug': self.slug})

    def __str__(self):
        return self.title