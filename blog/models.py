from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.text import Truncator, slugify

from core.models import TimeStampedModel
from django_ckeditor_5.fields import CKEditor5Field
from core.slugs import generate_unique_slug, slug_source_for
from .utils import blog_cover_upload_path, blog_cover_jpg_upload_path

import io

class PostCategory(models.Model):
    title = models.CharField(max_length=100, unique=True)
    title_en = models.CharField(
        max_length=100, blank=True,
        help_text="عنوان انگلیسی؛ در صورت پر بودن، اسلاگ از روی همین ساخته می‌شود.",
    )
    slug = models.SlugField(max_length=120, unique=True,
                            allow_unicode=True, blank=True)

    class Meta:
        verbose_name = 'دسته‌ی وبلاگ'
        verbose_name_plural = 'دسته‌های وبلاگ'
        ordering = ['title']

    def save(self, *args, **kwargs):
        if not self.slug:
            source, allow_unicode = slug_source_for(self)
            self.slug = generate_unique_slug(
                type(self), source, self.pk, allow_unicode=allow_unicode)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Tag(models.Model):
    title = models.CharField(max_length=50, unique=True)
    title_en = models.CharField(max_length=50, blank=True)
    slug = models.SlugField(max_length=70, unique=True,
                            allow_unicode=True, blank=True)

    class Meta:
        ordering = ['title']

    def save(self, *args, **kwargs):
        if not self.slug:
            source, allow_unicode = slug_source_for(self)
            self.slug = generate_unique_slug(
                type(self), source, self.pk, allow_unicode=allow_unicode)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Post(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'پیش‌نویس'
        PUBLISHED = 'published', 'منتشرشده'

    title = models.CharField(max_length=255)
    title_en = models.CharField(
        max_length=255, blank=True,
        help_text="عنوان انگلیسی؛ در صورت پر بودن، اسلاگ از روی همین ساخته می‌شود (توصیه‌ی اکید: همیشه پر شود).",
    )
    slug = models.SlugField(max_length=280, unique=True,
                            allow_unicode=True, blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='blog_posts', limit_choices_to={'is_staff': True},
    )
    category = models.ForeignKey(
        PostCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='posts',
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts')

    excerpt = models.CharField(
        max_length=300, blank=True,
        help_text="خلاصه‌ی کوتاه؛ در لیست پست‌ها و به‌عنوان پیش‌فرض meta description استفاده می‌شود.",
    )
    content = CKEditor5Field('محتوا', config_name='default')

    cover_image = models.ImageField(upload_to=blog_cover_upload_path, blank=True, null=True)
    cover_image_jpg = models.ImageField(
        upload_to=blog_cover_jpg_upload_path, blank=True, null=True, editable=False,
        help_text="نسخه‌ی خودکار JPG از cover_image، مخصوص og:image (چون تلگرام webp را در پیش‌نمایش لینک نشان نمی‌دهد).",
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)

    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)

    class Meta:
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['status', 'published_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            source, allow_unicode = slug_source_for(self)
            self.slug = generate_unique_slug(type(self), source, self.pk, allow_unicode=allow_unicode)

        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()

        plain_content = strip_tags(self.content) if self.content else ''
        if not self.excerpt:
            self.excerpt = Truncator(plain_content).words(30)
        if not self.meta_description:
            self.meta_description = Truncator(plain_content).words(25)

        self._process_cover_image_if_changed()

        super().save(*args, **kwargs)
    def _process_cover_image_if_changed(self):
        """
        """
        cover_changed = False
        if self.pk:
            try:
                old = Post.objects.get(pk=self.pk)
                cover_changed = old.cover_image != self.cover_image
            except Post.DoesNotExist:
                cover_changed = bool(self.cover_image)
        else:
            cover_changed = bool(self.cover_image)

        if cover_changed and self.cover_image:
            from core.images import convert_to_jpg, convert_to_webp
            self.cover_image.seek(0)
            raw_bytes = self.cover_image.read()
            self.cover_image = convert_to_webp(io.BytesIO(raw_bytes), max_size=(1600, 1600))
            self.cover_image_jpg = convert_to_jpg(io.BytesIO(raw_bytes), max_size=(1200, 630))

    @property
    def effective_meta_title(self):
        return self.meta_title or self.title

    def get_absolute_url(self):
        return reverse('blog:detail', kwargs={'slug': self.slug})

    def __str__(self):
        return self.title


class PostComment(TimeStampedModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='blog_comments',
    )
    guest_name = models.CharField(
        max_length=100, blank=True,
        help_text="برای مهمان الزامی است؛ برای کاربر لاگین‌شده فقط وقتی "
                   "در پروفایلش نامی ثبت نشده باشد، از همین استفاده می‌شود.",
    )
    text = models.TextField()
    is_approved = models.BooleanField(default=False)
    admin_reply = models.TextField(blank=True)
    admin_replied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['post', 'is_approved'])]

    def _profile_full_name(self):
        if not self.user_id:
            return ''
        return f"{self.user.first_name} {self.user.last_name}".strip()

    def clean(self):
        if not self.user_id and not self.guest_name:
            raise ValidationError("برای ثبت نظر به‌عنوان مهمان، وارد کردن نام الزامی است.")

        if self.user_id and not self._profile_full_name() and not self.guest_name:
            raise ValidationError("چون در پروفایل شما نامی ثبت نشده، لطفاً یک نام برای نمایش وارد کنید.")

    @property
    def display_name(self):
        if self.user_id:
            full_name = self._profile_full_name()
            if full_name:
                return full_name
            return self.guest_name or "کاربر سایت"
        return self.guest_name or "کاربر مهمان"

    def save(self, *args, **kwargs):
        if self.admin_reply and not self.admin_replied_at:
            self.admin_replied_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Comment #{self.pk} on {self.post.title}'