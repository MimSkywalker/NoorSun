"""

"""
from django.utils.text import slugify


def generate_unique_slug(model_cls, source_text, instance_pk=None, slug_field='slug', allow_unicode=False):
    """

    """
    base = slugify(source_text or '', allow_unicode=allow_unicode)
    if not base:
        base = 'item'

    slug = base
    counter = 1
    queryset = model_cls.objects.all()
    while queryset.filter(**{slug_field: slug}).exclude(pk=instance_pk).exists():
        counter += 1
        slug = f'{base}-{counter}'
    return slug


def slug_source_for(instance, english_field='title_en', persian_field='title'):
    """

    """
    english_value = (getattr(instance, english_field, '') or '').strip()
    if english_value:
        return english_value, False
    return getattr(instance, persian_field, '') or '', True