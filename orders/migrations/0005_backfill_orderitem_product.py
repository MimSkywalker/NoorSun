from django.db import migrations


def backfill_product(apps, schema_editor):
    OrderItem = apps.get_model('orders', 'OrderItem')

    for item in OrderItem.objects.select_related('variant').filter(
        product__isnull=True,
        variant__isnull=False,
    ):
        item.product_id = item.variant.product_id
        item.save(update_fields=['product'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0004_orderitem_product_alter_orderitem_variant"),
    ]

    operations = [
        migrations.RunPython(
            backfill_product,
            noop_reverse,
        ),
    ]
