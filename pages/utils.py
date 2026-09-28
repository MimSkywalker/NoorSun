import uuid
from django.utils import timezone
from django.core.validators import RegexValidator



def slide_desktop_upload_path(instance, filename):
    return f"pages/slides/{timezone.now():%Y/%m}/{uuid.uuid4().hex}.webp"


def slide_mobile_upload_path(instance, filename):
    return f"pages/slides/{timezone.now():%Y/%m}/mobile/{uuid.uuid4().hex}.webp"


link_validator = RegexValidator(
    regex=r'^(/|https?://)',
    message="لینک باید با / (مسیر داخلی) یا http:// و https:// شروع شود.",
)