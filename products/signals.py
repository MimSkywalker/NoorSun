from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from .models import ProductImage


@receiver(post_delete, sender=ProductImage)
def delete_product_image_file(sender, instance, **kwargs):
    """
    """
    if instance.image:
        instance.image.storage.delete(instance.image.name)
    if instance.image_jpg:
        instance.image_jpg.storage.delete(instance.image_jpg.name)


@receiver(pre_save, sender=ProductImage)
def delete_old_product_image(sender, instance, **kwargs):
    """
    """
    if not instance.pk:
        return

    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    old_image = old_instance.image
    new_image = instance.image
    if old_image and new_image and old_image.name != new_image.name:
        old_image.storage.delete(old_image.name)

    old_image_jpg = old_instance.image_jpg
    new_image_jpg = instance.image_jpg
    if old_image_jpg and new_image_jpg and old_image_jpg.name != new_image_jpg.name:
        old_image_jpg.storage.delete(old_image_jpg.name)