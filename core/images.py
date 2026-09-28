
import io
import uuid

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

DEFAULT_WEBP_QUALITY = 82
DEFAULT_JPG_QUALITY = 85


def _load_image(source):
    """

    """
    if hasattr(source, 'seek'):
        source.seek(0)
    image = Image.open(source)
    image = ImageOps.exif_transpose(image)
    return image


def convert_to_webp(source, max_size=(1600, 1600), quality=DEFAULT_WEBP_QUALITY):
    """

    """
    image = _load_image(source)

    if image.mode not in ('RGB', 'RGBA'):
        image = image.convert('RGBA') if 'A' in image.getbands() else image.convert('RGB')

    image.thumbnail(max_size, Image.LANCZOS)

    buffer = io.BytesIO()
    image.save(buffer, format='WEBP', quality=quality, method=6)
    buffer.seek(0)
    return ContentFile(buffer.read(), name=f'{uuid.uuid4().hex}.webp')


def convert_to_jpg(source, max_size=(1200, 630), quality=DEFAULT_JPG_QUALITY, background=(255, 255, 255)):
    """
    """
    image = _load_image(source)

    if image.mode in ('RGBA', 'LA', 'P'):
        image = image.convert('RGBA')
        canvas = Image.new('RGB', image.size, background)
        canvas.paste(image, mask=image.split()[-1])
        image = canvas
    else:
        image = image.convert('RGB')

    image.thumbnail(max_size, Image.LANCZOS)

    buffer = io.BytesIO()
    image.save(buffer, format='JPEG', quality=quality, optimize=True)
    buffer.seek(0)
    return ContentFile(buffer.read(), name=f'{uuid.uuid4().hex}.jpg')




def crop_to_webp(source, size, quality=DEFAULT_WEBP_QUALITY):
    """

    """
    image = _load_image(source)
    if image.mode not in ('RGB', 'RGBA'):
        image = image.convert('RGBA') if 'A' in image.getbands() else image.convert('RGB')
    image = ImageOps.fit(image, size, method=Image.LANCZOS, centering=(0.5, 0.5))
    buffer = io.BytesIO()
    image.save(buffer, format='WEBP', quality=quality, method=6)
    buffer.seek(0)
    return ContentFile(buffer.read(), name=f'{uuid.uuid4().hex}.webp')