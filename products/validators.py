from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

def validate_image_size(image):
    """
    Validate that the uploaded image does not exceed the maximum size.
    """
    max_size = 5 * 1024 * 1024  # 5 MB

    if image.size > max_size:
        raise ValidationError(
            "حجم تصویر نباید بیش از 5 مگابایت باشد"
        )
    
validate_image_extension = FileExtensionValidator(
    allowed_extensions=["jpg", "jpeg", "png", "webp"]
)