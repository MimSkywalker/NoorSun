import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import ProductVariant, StockMovement, RestockRequest
from notifications.sms import get_sms_service


logger = logging.getLogger(__name__)
sms_service = get_sms_service()


def record_stock_movement(
    variant,
    quantity_change,
    movement_type,
    note='',
    order=None,
    user=None,
):
    """
    Atomically updates variant stock, records the movement history,
    checks for low-stock alerts, and notifies restock subscribers
    when the variant becomes available again.

    quantity_change: integer; positive=increase, negative=decrease.
    This function is the only allowed point for changing ProductVariant.stock
    across the project. Both order sales/returns and manual admin updates
    must go through this function.
    """
    with transaction.atomic():
        variant = ProductVariant.objects.select_for_update().get(pk=variant.pk)
        old_stock = variant.stock
        new_stock = old_stock + quantity_change

        if new_stock < 0:
            raise ValueError(
                f"موجودی «{variant}» نمی‌تواند منفی شود "
                f"(موجودی فعلی={old_stock}, تغییر درخواستی={quantity_change})."
            )

        variant.stock = new_stock
        variant.save(update_fields=['stock'])

        movement = StockMovement.objects.create(
            variant=variant,
            movement_type=movement_type,
            quantity_change=quantity_change,
            stock_after=new_stock,
            note=note,
            order=order,
            created_by=user,
        )

        _check_low_stock_alert(variant)

        if old_stock == 0 and new_stock > 0:
            notify_restock_subscribers(variant)

    return movement


def _check_low_stock_alert(variant):
    threshold = variant.effective_low_stock_threshold

    if variant.stock <= threshold and not variant.low_stock_alert_sent:
        _send_low_stock_alert(variant)
        variant.low_stock_alert_sent = True
        variant.save(update_fields=['low_stock_alert_sent'])

    elif variant.stock > threshold and variant.low_stock_alert_sent:
        # Reset the flag when stock rises above the threshold so that
        # a new alert can be sent when stock becomes low again.
        variant.low_stock_alert_sent = False
        variant.save(update_fields=['low_stock_alert_sent'])


def _send_low_stock_alert(variant):
    phone = getattr(settings, 'ADMIN_ALERT_PHONE', '')

    if not phone:
        logger.warning(
            "ADMIN_ALERT_PHONE تنظیم نشده؛ هشدار موجودی کم ارسال نشد.")
        return

    message = f"هشدار موجودی کم: {variant} — موجودی فعلی: {variant.stock}"
    sms_service.send_message(phone, message)


def notify_restock_subscribers(variant):
    """
    Notifies all unnotified restock requests for this variant.
    Currently (Phase 7), this only uses Mock/logging behavior.
    In Phase 8, the internal sms_service and send_mail implementations
    can be replaced with real services without changing this function's
    signature or queue logic.
    """
    pending = RestockRequest.objects.filter(
        variant=variant,
        is_notified=False,
    )

    for req in pending:
        _send_restock_notification(req)
        req.is_notified = True
        req.notified_at = timezone.now()
        req.save(update_fields=['is_notified', 'notified_at'])


def _send_restock_notification(restock_request):
    message = f"کالای «{restock_request.variant.product.title}» دوباره موجود شد."

    if restock_request.phone_number:
        sms_service.send_message(
            restock_request.phone_number,
            message,
        )

    if restock_request.email:
        send_mail(
            subject="محصول مورد نظر شما دوباره موجود شد",
            message=message,
            from_email=None,
            recipient_list=[restock_request.email],
        )
