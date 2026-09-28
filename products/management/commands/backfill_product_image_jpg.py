import logging

from django.core.management.base import BaseCommand

from products.models import ProductImage
from products.utils import process_product_image_jpg

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "برای ProductImageهای قدیمی که image_jpg ندارند، از روی webp فعلی‌شان نسخه‌ی jpg می‌سازد."

    def handle(self, *args, **options):
        queryset = ProductImage.objects.filter(image_jpg='')
        total = queryset.count()
        done = 0
        failed = 0

        for product_image in queryset:
            try:
                product_image.image.seek(0)
                raw_bytes = product_image.image.read()
                import io
                jpg_content = process_product_image_jpg(io.BytesIO(raw_bytes))

                import uuid
                product_image.image_jpg.save(
                    f'{uuid.uuid4().hex}.jpg', jpg_content, save=True
                )
                done += 1
            except Exception:
                failed += 1
                logger.exception("خطا هنگام ساخت jpg برای ProductImage #%s", product_image.pk)
                self.stderr.write(self.style.ERROR(f"ProductImage #{product_image.pk} با خطا مواجه شد."))
                continue

        self.stdout.write(
            self.style.SUCCESS(f"{done} تصویر پردازش شد، {failed} خطا (از {total} مورد بررسی‌شده).")
        )