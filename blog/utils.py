
import io
import uuid
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.text import Truncator



def blog_cover_upload_path(instance, filename):
    date_path = timezone.now().strftime('%Y/%m')
    return f'blog/covers/{date_path}/{uuid.uuid4().hex}.webp'


def blog_cover_jpg_upload_path(instance, filename):
    date_path = timezone.now().strftime('%Y/%m')
    return f'blog/covers/{date_path}/og/{uuid.uuid4().hex}.jpg'