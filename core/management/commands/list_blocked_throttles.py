from django.core.management.base import BaseCommand
from django.core.cache import cache


class Command(BaseCommand):
    help = "نمایش کلیدهای throttle مسدودشده‌ی فعلی (برای بررسی دستی/دیباگ)."

    def add_arguments(self, parser):
        parser.add_argument('--scope', type=str, default=None, help='فیلتر بر اساس scope خاص')

    def handle(self, *args, **options):
        # django-redis از طریق cache.keys با پشتیبانی از الگو کار می‌کند
        pattern = f"throttle:{options['scope']}:*:blocked:*" if options['scope'] else "throttle:*:blocked:*"
        try:
            keys = cache.keys(pattern)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"خطا در خواندن از Redis: {e}"))
            return

        if not keys:
            self.stdout.write("هیچ IP/شناسه‌ی مسدودی در حال حاضر وجود ندارد.")
            return

        for key in keys:
            ttl = cache.ttl(key)
            self.stdout.write(f"{key} — {ttl} ثانیه تا رفع مسدودی")