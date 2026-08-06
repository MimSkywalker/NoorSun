import logging
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from orders.models import Order
from orders.utils import release_order_stock


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Expire unpaid pending orders that have exceeded the payment timeout."

    def handle(self, *args, **options):

        # Calculate the expiration cutoff time.
        timeout = timedelta(
            minutes=settings.ORDER_PAYMENT_TIMEOUT_MINUTES
        )

        cutoff = timezone.now() - timeout

        # Find pending orders whose payment window has expired.
        stale_order_ids = list(
            Order.objects.filter(
                status=Order.Status.PENDING,
                created_at__lt=cutoff,
            ).values_list('id', flat=True)
        )

        # Track successful and failed expirations.
        expired_count = 0
        failed_count = 0

        for order_id in stale_order_ids:
            try:
                # Release reserved stock and mark the order as expired.
                if release_order_stock(
                    order_id,
                    Order.Status.EXPIRED
                ):
                    expired_count += 1

            except Exception:
                # Log the full traceback and continue with other orders.
                failed_count += 1

                logger.exception(
                    "خطا هنگام expire کردن سفارش #%s",
                    order_id
                )

                self.stderr.write(
                    self.style.ERROR(
                        f"سفارش #{order_id} با خطا مواجه شد؛ رد شد."
                    )
                )

                continue

        # Report successful and failed expirations.
        self.stdout.write(
            self.style.SUCCESS(
                f"{expired_count} سفارش منقضی شد. "
                f"{failed_count} سفارش با خطا مواجه شد "
                f"(از {len(stale_order_ids)} مورد بررسی‌شده)."
            )
        )
