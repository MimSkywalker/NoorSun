import uuid
import io
from PIL import Image
from django.core.files.base import ContentFile


def product_image_upload_path(instance, _filename):
    """
    Generate a unique upload path for product images.

    Images are stored in a directory named after the product ID,
    and each file is assigned a unique UUID-based filename.
    """
    unique_filename = f"{uuid.uuid4()}.webp"

    return f"products/{instance.product.id}/{unique_filename}"




def process_product_image(image_field):
    image = Image.open(image_field)

    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1])
        image = background
    else:
        image = image.convert("RGB")

    image.thumbnail((1200, 1200), Image.Resampling.LANCZOS)

    output = io.BytesIO()

    image.save(
        output,
        format="WEBP",
        quality=95,
        optimize=True,
    )

    output.seek(0)

    return ContentFile(output.read())