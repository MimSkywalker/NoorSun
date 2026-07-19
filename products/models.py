from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

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
        verbose_name = "Feature value"
        verbose_name_plural = "Feature values"
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

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def clean(self):
        if self.replacement_product_id and self.replacement_product_id == self.id:
            raise ValidationError("محصول نمی‌تواند جایگزین خودش باشد.")

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

    class Meta:
        verbose_name = "تنوع محصول"
        verbose_name_plural = "تنوع‌های محصول"
        ordering = ['-created_at']

    def __str__(self):
        attrs = ", ".join(str(v) for v in self.attribute_values.all())
        return f"{self.product.title} ({attrs or 'بدون ویژگی'})"

    @property
    def is_in_stock(self):
        return self.stock > 0 and self.is_active
