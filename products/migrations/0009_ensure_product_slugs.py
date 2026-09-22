from django.db import migrations
from django.utils.text import slugify


def ensure_slugs(apps, schema_editor):
    Product = apps.get_model('products', 'Product')
    for product in Product.objects.filter(slug=''):
        base_slug = slugify(product.title, allow_unicode=True)
        slug = base_slug
        counter = 1
        while Product.objects.filter(slug=slug).exclude(pk=product.pk).exists():
            counter += 1
            slug = f'{base_slug}-{counter}'
        product.slug = slug
        product.save(update_fields=['slug'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [('products', '0007_review')]
    operations = [migrations.RunPython(ensure_slugs, noop_reverse)]