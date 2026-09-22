import threading

from django.core.management.base import BaseCommand

from products.models import ProductVariant, StockMovement
from products.stock import record_stock_movement


class Command(BaseCommand):
    help = 'Test concurrent stock movements.'

    def handle(self, *args, **options):
        variant = ProductVariant.objects.get(pk=18)

        initial_stock = variant.stock
        quantity = 2
        thread_count = 10

        results = []
        lock = threading.Lock()

        def worker():
            try:
                record_stock_movement(
                    variant=variant,
                    quantity_change=-quantity,
                    movement_type=StockMovement.MovementType.SALE,
                )

                with lock:
                    results.append(True)

            except ValueError:
                with lock:
                    results.append(False)

        threads = [
            threading.Thread(target=worker)
            for _ in range(thread_count)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        variant.refresh_from_db()

        successful = sum(results)
        failed = len(results) - successful

        self.stdout.write(f'Initial stock: {initial_stock}')
        self.stdout.write(f'Successful movements: {successful}')
        self.stdout.write(f'Failed movements: {failed}')
        self.stdout.write(f'Final stock: {variant.stock}')

        expected_max_successful = initial_stock // quantity

        if successful > expected_max_successful:
            self.stdout.write(
                self.style.ERROR(
                    'FAIL: Successful movements exceeded available stock.'
                )
            )
            return

        if variant.stock < 0:
            self.stdout.write(
                self.style.ERROR(
                    'FAIL: Stock became negative.'
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                'PASS: Concurrent stock test completed successfully.'
            )
        )
