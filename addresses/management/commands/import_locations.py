import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from addresses.models import City, Province


class Command(BaseCommand):
    help = 'وارد کردن استان‌ها و شهرهای ایران از فایل‌های JSON محلی (fixtures/province.json و cities.json)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--province-file',
            default=str(Path(settings.BASE_DIR) / 'addresses' /
                        'fixtures' / 'province.json'),
            help='مسیر فایل province.json',
        )
        parser.add_argument(
            '--city-file',
            default=str(Path(settings.BASE_DIR) / 'addresses' /
                        'fixtures' / 'cities.json'),
            help='مسیر فایل cities.json',
        )

    def handle(self, *args, **options):
        province_path = Path(options['province_file'])
        city_path = Path(options['city_file'])

        if not province_path.exists():
            raise CommandError(f'فایل استان‌ها پیدا نشد: {province_path}')
        if not city_path.exists():
            raise CommandError(f'فایل شهرها پیدا نشد: {city_path}')

        province_data = self._load_json(province_path)
        city_data = self._load_json(city_path)

        with transaction.atomic():
            province_id_map = self._import_provinces(province_data)
            self._import_cities(city_data, province_id_map)

        self.stdout.write(self.style.SUCCESS(
            f'وارد شد: {Province.objects.count()} استان و {City.objects.count()} شهر.'
        ))

    def _load_json(self, path):
        with open(path, encoding='utf-8') as f:
            raw = json.load(f)
        # بعضی نسخه‌های این JSON داخل کلید "RECORDS" پیچیده شده‌اند
        if isinstance(raw, dict) and 'RECORDS' in raw:
            return raw['RECORDS']
        return raw

    def _import_provinces(self, records):
        """
        خروجی: دیکشنری {id قدیمی در JSON: نمونه‌ی Province ساخته‌شده}
        چون ممکنه id های خود دیتابیس ما با id های فایل یکی نباشه،
        نگاشت جداگانه نگه می‌داریم به‌جای اتکا به pk خودکار جنگو.
        """
        id_map = {}
        created_count = 0
        for record in records:
            province, created = Province.objects.get_or_create(
                title=record['title'].strip()
            )
            id_map[record['id']] = province
            created_count += created

        self.stdout.write(
            f'{created_count} استان جدید ساخته شد ({len(records)} رکورد پردازش شد).')
        return id_map

    def _import_cities(self, records, province_id_map):
        created_count = 0
        skipped = 0
        for record in records:
            province = province_id_map.get(record.get('province_id'))
            if province is None:
                skipped += 1
                continue

            _, created = City.objects.get_or_create(
                province=province,
                title=record['title'].strip(),
            )
            created_count += created

        self.stdout.write(f'{created_count} شهر جدید ساخته شد.')
        if skipped:
            self.stdout.write(self.style.WARNING(
                f'{skipped} رکورد شهر به‌دلیل نداشتن استان معتبر رد شد.'
            ))
