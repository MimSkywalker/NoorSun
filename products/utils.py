import io
import uuid

from PIL import Image, ImageOps
from django.core.files.base import ContentFile


def product_image_upload_path(instance, _filename):
    """
    """
    unique_filename = f"{uuid.uuid4()}.webp"
    return f"products/{instance.product.id}/{unique_filename}"


def product_image_jpg_upload_path(instance, _filename):
    """
    """
    unique_filename = f"{uuid.uuid4()}.jpg"
    return f"products/{instance.product.id}/og/{unique_filename}"


def process_product_image(image_field):
    """
    """
    image = Image.open(image_field)
    image = ImageOps.exif_transpose(image)  # ← خط جدید: رفع چرخش عکس‌های موبایل

    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1])
        image = background
    else:
        image = image.convert("RGB")

    image.thumbnail((1200, 1200), Image.Resampling.LANCZOS)

    output = io.BytesIO()
    image.save(output, format="WEBP", quality=95, optimize=True)
    output.seek(0)

    return ContentFile(output.read())


def process_product_image_jpg(image_field, max_size=(1200, 630), quality=85):
    """
    """
    image = Image.open(image_field)
    image = ImageOps.exif_transpose(image)

    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1])
        image = background
    else:
        image = image.convert("RGB")

    image.thumbnail(max_size, Image.Resampling.LANCZOS)

    output = io.BytesIO()
    image.save(output, format="JPEG", quality=quality, optimize=True)
    output.seek(0)

    return ContentFile(output.read())