from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from .models import ProductImage


@receiver(post_delete, sender=ProductImage)
def delete_product_image_file(sender, instance, **kwargs):
    """
    Delete the image file from storage when the ProductImage is deleted.
    """
    if instance.image:
        instance.image.storage.delete(instance.image.name)


@receiver(pre_save, sender=ProductImage)
def delete_old_product_image(sender, instance, **kwargs):
    """
    Delete the old image file when a new one is uploaded.
    """
    if not instance.pk:
        return

    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    old_image = old_instance.image
    new_image = instance.image

    if (
        old_image
        and new_image
        and old_image.name != new_image.name
    ):
        old_image.storage.delete(old_image.name)