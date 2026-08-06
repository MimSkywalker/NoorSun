from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView, CreateView

from addresses.models import Address
from products.models import ProductVariant

from .gateways import get_gateway
from .models import (
    CartItem,
    InsufficientStockError,
    Order,
    Payment,
    ProductInactiveError,
    RefundRequest,
    VariantInactiveError,
    create_order_from_cart,
)

from .utils import (
    check_and_expire_order,
    get_or_create_cart,
    release_order_stock,
)


def _is_ajax(request):
    # Check if the request is sent via AJAX
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def _cart_json(cart, **extra):
    # Return cart data as a JSON response
    data = {
        'items_count': cart.items_count,
        'subtotal': cart.subtotal,
        'shipping_cost': cart.shipping_cost,
        'packaging_cost': cart.packaging_cost,
        'total': cart.total,
    }
    data.update(extra)
    return JsonResponse(data)


class CartDetailView(TemplateView):
    # Display the current shopping cart
    template_name = 'orders/cart_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cart'] = get_or_create_cart(self.request)
        return context


class CartAddView(View):
    # Add a product variant to the current cart
    def post(self, request, variant_id):

        # Get the selected product variant
        variant = get_object_or_404(ProductVariant, pk=variant_id)

        if not variant.product.is_active or not variant.is_active:
            messages.error(request, "این محصول در حال حاضر ناموجود است.")
            if _is_ajax(request):
                return JsonResponse({'error': True, 'message': 'محصول ناموجود است.'})
            return redirect('products:detail', pk=variant.product.pk)

        # Ensure a valid quantity
        try:
            quantity = int(request.POST.get('quantity', 1))
        except (TypeError, ValueError):
            quantity = 1
        quantity = max(quantity, 1)

        # Get or create the current cart
        cart = get_or_create_cart(request)

        # Get or create the cart item
        item, created = CartItem.objects.get_or_create(
            cart=cart, variant=variant, defaults={'quantity': 0}
        )
        item.quantity += quantity

        # Never exceed available stock
        item.quantity = min(item.quantity, variant.stock)

        if item.quantity < 1:
            item.delete()
            messages.error(request, "این کالا در حال حاضر موجود نیست.")
            if _is_ajax(request):
                return _cart_json(cart, error=True)
            return redirect('products:list')

        item.save()
        messages.success(request, "به سبد خرید اضافه شد.")
        if _is_ajax(request):
            return _cart_json(cart, error=False)
        return redirect('orders:cart_detail')


class CartUpdateItemView(View):
    # Update the quantity of a cart item

    def post(self, request, item_id):
        cart = get_or_create_cart(request)

        # Prevent IDOR by ensuring the item belongs to the current cart
        item = get_object_or_404(CartItem, pk=item_id, cart=cart)

        try:
            quantity = int(request.POST.get('quantity', 1))
        except (TypeError, ValueError):
            quantity = 1

        if quantity < 1:
            item.delete()
            messages.success(request, "کالا از سبد حذف شد.")
        else:
            is_unavailable = not item.variant.product.is_active or not item.variant.is_active
            if is_unavailable and quantity > item.quantity:
                messages.error(
                    request, "این کالا دیگر قابل خرید نیست و نمی‌توانید تعدادش را افزایش دهید.")
                if _is_ajax(request):
                    return _cart_json(cart, error=True)
                return redirect('orders:cart_detail')

            if quantity > item.variant.stock:
                quantity = item.variant.stock
                messages.warning(request, "تعداد به حداکثر موجودی محدود شد.")
            item.quantity = quantity
            item.save(update_fields=['quantity'])
            messages.success(request, "تعداد به‌روزرسانی شد.")

        if _is_ajax(request):
            return _cart_json(cart)
        return redirect('orders:cart_detail')


class CartRemoveItemView(View):
    # Remove an item from the current cart
    def post(self, request, item_id):
        cart = get_or_create_cart(request)
        item = get_object_or_404(CartItem, pk=item_id, cart=cart)
        item.delete()
        messages.success(request, "کالا از سبد حذف شد.")

        # Return JSON for AJAX, otherwise redirec
        if _is_ajax(request):
            return _cart_json(cart)
        return redirect('orders:cart_detail')


class CheckoutView(LoginRequiredMixin, View):

    """
    Handle checkout and order creation
    """

    template_name = 'orders/checkout.html'

    # Display checkout page with active cart and saved addresses
    def get(self, request):
        cart = get_or_create_cart(request)

        # Load addresses with related city and province in a single query
        addresses = Address.objects.filter(
            user=request.user).select_related('city', 'city__province')

        # Prevent checkout with an empty cart
        if not cart.items.exists():
            messages.error(request, "سبد خرید شما خالی است.")
            return redirect('orders:cart_detail')
        return render(request, self.template_name, {'cart': cart, 'addresses': addresses})

    # Create a finalized order from the current cart

    def post(self, request):
        cart = get_or_create_cart(request)
        address_id = request.POST.get('address_id')

        # Ensure the selected address belongs to the current user
        address = get_object_or_404(
            Address,
            pk=address_id,
            user=request.user
        )

        try:
            order = create_order_from_cart(cart, request.user, address)

        except ProductInactiveError as e:
            messages.error(
                request,
                f"محصول «{e.product}» دیگر موجود نیست و از سبد شما حذف خواهد شد."
            )
            cart.items.filter(
                variant__product=e.product
            ).delete()
            return redirect('orders:cart_detail')

        except VariantInactiveError as e:
            messages.error(
                request,
                f"«{e.variant}» دیگر قابل خرید نیست و از سبد شما حذف خواهد شد."
            )
            cart.items.filter(
                variant=e.variant
            ).delete()
            return redirect('orders:cart_detail')

        except InsufficientStockError as e:
            messages.error(
                request,
                f"موجودی «{e.variant}» کافی نیست (موجودی فعلی: {e.available})."
            )
            return redirect('orders:cart_detail')

        except ValueError as e:
            messages.error(request, str(e))
            return redirect('orders:cart_detail')

        # After creating the order, start the payment process directly.
        return redirect('orders:payment_initiate', pk=order.pk)


class OrderListView(LoginRequiredMixin, ListView):

    """Display the current user's order history"""

    template_name = 'orders/order_list.html'
    context_object_name = 'orders'
    paginate_by = 10

    # Return only the authenticated user's orders
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items')


class OrderDetailView(LoginRequiredMixin, DetailView):
    """
    Display details of a single order
    """
    model = Order
    template_name = 'orders/order_detail.html'
    context_object_name = 'order'

    # Prevent users from accessing other users' orders (IDOR protection)
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items')

    def get_object(self, queryset=None):
        order = super().get_object(queryset)
        return check_and_expire_order(order)


class OrderInvoiceView(LoginRequiredMixin, DetailView):
    """Display order invoice as an HTML page"""

    template_name = 'orders/invoice.html'
    context_object_name = 'order'

    #  Return only the current user's orders to prevent unauthorized access
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items')


class OrderInvoicePDFView(LoginRequiredMixin, DetailView):
    """Generate and download order invoice as a PDF file"""
    context_object_name = 'order'

    # Return only the current user's orders to prevent IDOR vulnerabilities
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items')

    # Convert invoice HTML template into a PDF response
    def get(self, request, *args, **kwargs):
        # Retrieve the requested order object
        self.object = self.get_object()

        # Render invoice template as HTML string for PDF generation
        html_string = render_to_string(
            'orders/invoice.html', {'order': self.object, 'is_pdf': True})

        # Convert HTML content into PDF using WeasyPrint
        from weasyprint import HTML
        pdf_file = HTML(string=html_string,
                        base_url=request.build_absolute_uri('/')).write_pdf()

        # Return PDF file as HTTP response
        response = HttpResponse(pdf_file, content_type='application/pdf')

        # Force browser to download the generated invoice
        response['Content-Disposition'] = f'attachment; filename="invoice-{self.object.tracking_code}.pdf"'
        return response


class PaymentInitiateView(LoginRequiredMixin, View):
    """
    Starts a new payment attempt for an order.

    Failed attempts remain in the payment history, while each retry
    creates a new Payment record.
    """

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk, user=request.user)
        order = check_and_expire_order(order)

        if order.status == Order.Status.EXPIRED:
            messages.error(
                request,
                "زمان پرداخت این سفارش به پایان رسیده و لغو شد.",
            )
            return redirect("orders:detail", pk=order.pk)

        if order.status != Order.Status.PENDING_PAYMENT:
            messages.info(request, "این سفارش قبلاً پردازش شده است.")
            return redirect("orders:detail", pk=order.pk)

        payment = Payment.objects.create(
            order=order,
            gateway=settings.PAYMENT_GATEWAY,
            amount=order.total,
            status=Payment.Status.PENDING,
        )

        # Use the configured gateway to start the payment.
        gateway = get_gateway()
        result = gateway.request_payment(payment)

        if not result.success:
            payment.status = Payment.Status.FAILED
            payment.raw_response = {"error": result.error_message}
            payment.save(update_fields=["status", "raw_response"])

            messages.error(
                request,
                "اتصال به درگاه پرداخت با خطا مواجه شد. دوباره تلاش کنید.",
            )
            return redirect("orders:detail", pk=order.pk)

        # Store the gateway authority for the callback and verification step.
        payment.authority = result.authority or ""
        payment.save(update_fields=["authority"])

        return redirect(result.redirect_url)


class FakeGatewayView(LoginRequiredMixin, View):
    """
    Simulates a payment gateway for development and testing.

    It uses the same callback flow as a real gateway without making
    external requests.
    """

    def get(self, request, payment_id):
        payment = get_object_or_404(
            Payment,
            pk=payment_id,
            order__user=request.user,
            status=Payment.Status.PENDING,
        )
        return render(
            request,
            "orders/fake_gateway.html",
            {"payment": payment},
        )

    def post(self, request, payment_id):
        payment = get_object_or_404(
            Payment,
            pk=payment_id,
            order__user=request.user,
            status=Payment.Status.PENDING,
        )

        # Simulate the gateway result selected by the user.
        result = request.POST.get("result")

        callback_url = reverse("orders:payment_callback")
        return redirect(
            f"{callback_url}?authority={payment.authority}&result={result}"
        )


class PaymentCallbackView(View):
    """
    Handles the payment gateway callback.

    Payment verification is delegated to the configured gateway implementation.
    The callback is idempotent and ignores already finalized payments.
    """

    def get(self, request):
        authority = request.GET.get("authority")
        payment = get_object_or_404(Payment, authority=authority)

        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(pk=payment.pk)

            if payment.status != Payment.Status.PENDING:
                # Ignore duplicate callbacks for finalized payments.
                return self._redirect_result(payment)

            order = Order.objects.select_for_update().get(pk=payment.order_id)

            if order.status != Order.Status.PENDING_PAYMENT:
                # The order was finalized concurrently, so this payment is no longer valid.
                payment.status = Payment.Status.FAILED
                payment.raw_response = {"error": "order_no_longer_pending"}
                payment.save(update_fields=["status", "raw_response"])
                messages.error(request, "زمان این سفارش به پایان رسیده بود.")
                return redirect("orders:detail", pk=order.pk)

            # Always verify through the gateway stored on the Payment.
            gateway = get_gateway(payment.gateway)
            verify_result = gateway.verify_payment(payment, request.GET.dict())

            if verify_result.success:
                payment.status = Payment.Status.SUCCESS
                payment.ref_id = verify_result.ref_id or ""
                payment.raw_response = verify_result.raw_response
                payment.paid_at = timezone.now()
                payment.save(
                    update_fields=[
                        "status",
                        "ref_id",
                        "raw_response",
                        "paid_at",
                    ]
                )

                order.status = Order.Status.PROCESSING
                order.save(update_fields=["status", "updated_at"])

                messages.success(
                    request,
                    f"پرداخت با موفقیت انجام شد. کد پیگیری: {order.tracking_code}",
                )
            else:
                payment.status = Payment.Status.FAILED
                payment.raw_response = verify_result.raw_response
                payment.save(update_fields=["status", "raw_response"])

                # Keep the order pending so the customer can retry payment.
                messages.error(
                    request,
                    verify_result.error_message or "پرداخت ناموفق بود.",
                )

        return redirect("orders:detail", pk=payment.order_id)

    def _redirect_result(self, payment):
        return redirect("orders:detail", pk=payment.order_id)


class PaymentCancelView(LoginRequiredMixin, View):
    """
    Handles manual payment cancellation before the payment timeout.

    Stock release is delegated to the shared idempotent helper.
    """

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, user=request.user)
        released = release_order_stock(order.pk, Order.Status.CANCELED)

        if released:
            messages.success(request, "سفارش لغو شد و موجودی کالاها آزاد شد.")
        else:
            messages.info(
                request,
                "این سفارش دیگر قابل لغو نیست (احتمالاً پرداخت شده یا قبلاً لغو شده).",
            )

        return redirect("orders:detail", pk=order.pk)


class RefundRequestCreateView(LoginRequiredMixin, CreateView):
    # Create a refund request using the RefundRequest model.
    model = RefundRequest

    # The user is only allowed to submit the refund reason.
    # Sensitive fields such as order, payment, and user are set server-side.
    fields = ['reason']

    # Template used to display the refund request form.
    template_name = 'orders/refund_request_form.html'

    def dispatch(self, request, *args, **kwargs):
        # Retrieve the requested order while ensuring that:
        # 1. The order belongs to the currently authenticated user.
        # 2. The order is in a status that allows a refund request.
        #
        # Checking user=request.user also prevents IDOR attacks,
        # because a user cannot access another user's order by changing order_id.
        self.order = get_object_or_404(
            Order,
            pk=kwargs['order_id'],
            user=request.user,
            status__in=[Order.Status.PROCESSING,
                        Order.Status.SHIPPED, Order.Status.DELIVERED],
        )

        # Only orders with at least one successful payment
        # are eligible for a refund request.
        #
        # If multiple successful payments exist, use the most recent
        # successful payment based on paid_at.
        self.successful_payment = self.order.payments.filter(
            status=Payment.Status.SUCCESS
        ).order_by('-paid_at').first()

        # Do not allow a refund request if no successful payment exists.
        if not self.successful_payment:
            messages.error(
                request, "برای این سفارش پرداخت موفقی ثبت نشده است.")
            return redirect('orders:detail', pk=self.order.pk)

        # Continue with the normal CreateView processing
        # after all authorization and payment checks have passed.
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Set the order server-side instead of accepting it from the user.
        # This prevents the user from attaching the refund request
        # to a different order.
        form.instance.order = self.order

        # Associate the refund request with the verified successful payment.
        # This value is also controlled by the server.
        form.instance.payment = self.successful_payment

        # Associate the refund request with the currently authenticated user.
        # The user cannot choose or modify this value through the form.
        form.instance.user = self.request.user

        # Inform the user that the refund request was successfully created.
        messages.success(
            self.request, "درخواست بازگشت وجه شما ثبت شد و در حال بررسی است.")

        # Save the RefundRequest and continue the normal CreateView flow.
        return super().form_valid(form)

    def get_success_url(self):
        # After successfully creating the refund request,
        # redirect the user back to the order detail page.
        return reverse_lazy('orders:detail', kwargs={'pk': self.order.pk})
