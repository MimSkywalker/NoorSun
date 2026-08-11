from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from core.models import TimeStampedModel

from .utils import product_image_upload_path, process_product_image
from .validators import validate_image_size, validate_image_extension


class Category(TimeStampedModel):

    """Stores hierarchical product categories."""

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"
        ordering = ['name']

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class Brand(TimeStampedModel):

    """Stores product brand information."""

    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "برند"
        verbose_name_plural = "برندها"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class Attribute(TimeStampedModel):

    """Defines product attributes such as color or size."""

    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "ویژگی"
        verbose_name_plural = "ویژگی‌ها"
        ordering = ['name']

    def __str__(self):
        return self.name


class AttributeValue(TimeStampedModel):

    """Stores available values for each product attribute."""

    attribute = models.ForeignKey(
        Attribute,
        on_delete=models.CASCADE,
        related_name='values',
    )
    value = models.CharField(max_length=100)

    class Meta:
        verbose_name = "ویژگی محصول"
        verbose_name_plural = "ویژگی محصولات"
        unique_together = ('attribute', 'value')
        ordering = ['attribute', 'value']

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


class Product(TimeStampedModel):
    """Stores main product information."""
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
    )
    is_active = models.BooleanField(default=True)
    replacement_product = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replaced_by',
        help_text="در صورت ناموجود شدن دائمی، محصول جایگزین معرفی می‌شود.",
    )

    sales_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['-sales_count']),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        if self.replacement_product_id and self.replacement_product_id == self.id:
            raise ValidationError("محصول نمی‌تواند جایگزین خودش باشد.")

    @property
    def main_image(self):
        images = list(self.images.all())
        return images[0] if images else None

    @property
    def default_variant(self):
        variants = list(self.variants.all())
        return variants[0] if variants else None

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)


class ProductImage(TimeStampedModel):
    """Stores images associated with a product."""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
    )
    image = models.ImageField(
        upload_to=product_image_upload_path,
        validators=[validate_image_size, validate_image_extension],)

    is_main = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'تصویر محصول'
        verbose_name_plural = "تصویر محصولات"
        ordering = ['order']

    def __str__(self):
        return f"Image | {self.order} - {self.product.title}"

    def clean(self):
        if self.product_id:
            qs = ProductImage.objects.filter(product_id=self.product_id)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.count() >= 6:
                raise ValidationError(
                    "هر محصول حداکثر می‌تواند ۶ تصویر داشته باشد.")

    def save(self, *args, **kwargs):

        self.full_clean()

        if self.pk:
            old_image = ProductImage.objects.get(pk=self.pk).image

            if old_image.name != self.image.name:
                processed = process_product_image(self.image)

                self.image.save(
                    self.image.name,
                    processed,
                    save=False,
                )

        else:
            processed = process_product_image(self.image)

            self.image.save(
                self.image.name,
                processed,
                save=False,
            )

        super().save(*args, **kwargs)

        if self.is_main:
            ProductImage.objects.filter(
                product=self.product
            ).exclude(
                pk=self.pk
            ).update(
                is_main=False
            )


class ProductVariant(TimeStampedModel):
    """Represents a purchasable product variant with its own price and stock."""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants',
    )
    attribute_values = models.ManyToManyField(
        AttributeValue,
        related_name='variants',
        blank=True,
    )
    sku = models.CharField(max_length=64, unique=True)
    price = models.DecimalField(max_digits=12, decimal_places=0)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    discount_price = models.DecimalField(
        max_digits=10, decimal_places=0, null=True, blank=True
    )

    promo_price = models.DecimalField(
        max_digits=12, decimal_places=0, null=True, blank=True)
    promo_start = models.DateTimeField(null=True, blank=True)
    promo_end = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "تنوع محصول"
        verbose_name_plural = "تنوع‌های محصول"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['price']),
            models.Index(fields=['discount_price']),
        ]

    def __str__(self):
        attrs = ", ".join(str(v) for v in self.attribute_values.all())
        return f"{self.product.title} ({attrs or 'بدون ویژگی'})"

    def clean(self):

        if self.promo_price is not None and (not self.promo_start or not self.promo_end):
            raise ValidationError(
                "برای تخفیف زمان‌دار، تاریخ شروع و پایان الزامی است.")

        if self.promo_start and self.promo_end and self.promo_start >= self.promo_end:
            raise ValidationError(
                "تاریخ شروع تخفیف زمان‌دار باید قبل از تاریخ پایان باشد.")

    @property
    def is_promo_active(self):
        if self.promo_price is None or not self.promo_start or not self.promo_end:
            return False
        now = timezone.now()
        return self.promo_start <= now <= self.promo_end

    _campaign_price_cache = None

    def active_campaign_price(self):
        if self._campaign_price_cache is not None or hasattr(
            self, '_campaign_price_cache_set'
        ):
            return self._campaign_price_cache

        # Fallback for contexts where campaign prices were not precomputed.
        best_price = None

        for campaign in Campaign.objects.filter(
            is_active=True
        ).prefetch_related(
            'categories',
            'brands',
            'products',
        ):
            if campaign.is_running and campaign.covers_variant(self):
                price = campaign.price_for(self)

                if best_price is None or price < best_price:
                    best_price = price

        return best_price

    @property
    def is_in_stock(self):
        return self.stock > 0 and self.is_active

    @property
    def final_price(self):
        candidates = [self.price]

        if self.discount_price is not None:
            candidates.append(self.discount_price)

        if self.is_promo_active:
            candidates.append(self.promo_price)

        campaign_price = self.active_campaign_price()
        if campaign_price is not None:
            candidates.append(campaign_price)

        return min(candidates)

    @property
    def has_discount(self):
        return self.final_price < self.price


class Campaign(TimeStampedModel):
    class DiscountType(models.TextChoices):
        PERCENTAGE = 'percentage', 'درصدی'
        FIXED = 'fixed', 'مبلغ ثابت'

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)

    discount_type = models.CharField(
        max_length=10, choices=DiscountType.choices)
    value = models.DecimalField(max_digits=12, decimal_places=0)

    # Optional scope restrictions for the campaign.
    categories = models.ManyToManyField(
        'Category', blank=True, related_name='campaigns')
    brands = models.ManyToManyField(
        'Brand', blank=True, related_name='campaigns')
    products = models.ManyToManyField(
        'Product', blank=True, related_name='campaigns')

    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['start_at', 'end_at', 'is_active']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def clean(self):
        if self.start_at and self.end_at and self.start_at >= self.end_at:
            raise ValidationError(
                "تاریخ شروع کمپین باید قبل از تاریخ پایان باشد.")

    @property
    def is_running(self):
        if not self.is_active:
            return False
        now = timezone.now()
        return self.start_at <= now <= self.end_at

    def covers_variant(self, variant):
        """Check whether this campaign applies to the given variant."""
        product = variant.product  # باید از قبل با select_related لود شده باشد

        product_ids = {p.pk for p in self.products.all()}
        if product.pk in product_ids:
            return True

        category_ids = {c.pk for c in self.categories.all()}
        if product.category_id and product.category_id in category_ids:
            return True

        brand_ids = {b.pk for b in self.brands.all()}
        if product.brand_id and product.brand_id in brand_ids:
            return True

        return False

    def price_for(self, variant):
        """Calculate the variant price after applying this campaign."""
        base = variant.price
        if self.discount_type == self.DiscountType.PERCENTAGE:
            return base - (base * self.value / 100)
        return max(base - self.value, 0)
