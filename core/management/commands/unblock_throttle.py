# core/management/commands/unblock_throttle.py
from django.core.management.base import BaseCommand
from core.throttling import reset_throttle


class Command(BaseCommand):
    help = "رفع دستی مسدودی throttle برای یک IP یا شناسه (پشتیبانی از کاربر واقعی)."

    def add_arguments(self, parser):
        parser.add_argument('scope', type=str)
        parser.add_argument('--ip', type=str, default=None)
        parser.add_argument('--identifier', type=str, default=None)

    def handle(self, *args, **options):
        reset_throttle(scope=options['scope'], ip=options['ip'] or '', identifier=options['identifier'])
        self.stdout.write(self.style.SUCCESS("رفع مسدودی انجام شد."))