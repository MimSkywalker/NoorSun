from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import Slide, StaticPage
from .services import invalidate_nav_cache


@receiver([post_save, post_delete], sender=StaticPage)
def clear_nav_cache(sender, **kwargs):
    invalidate_nav_cache()


@receiver(post_delete, sender=Slide)
def delete_slide_files(sender, instance, **kwargs):
    for field in (instance.image, instance.image_mobile):
        if field:
            field.storage.delete(field.name)


@receiver(pre_save, sender=Slide)
def delete_old_slide_files(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    for name in ('image', 'image_mobile'):
        old_file = getattr(old, name)
        new_file = getattr(instance, name)
        if old_file and old_file.name != (new_file.name if new_file else None):
            old_file.storage.delete(old_file.name)