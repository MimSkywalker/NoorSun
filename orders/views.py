from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin


from products.models import ProductVariant
from .models import CartItem, Order, create_order_from_cart, InsufficientStockError
from .utils import get_or_create_cart
from addresses.models import Address


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
        address = get_object_or_404(Address, pk=address_id, user=request.user)

        try:
            order = create_order_from_cart(cart, request.user, address)
        except InsufficientStockError as e:
            messages.error(
                request,
                f"موجودی «{e.variant}» کافی نیست (موجودی فعلی: {e.available})."
            )
            return redirect('orders:cart_detail')

        # Handle insufficient inventory
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('orders:cart_detail')

        messages.success(
            request, f"سفارش شما با کد رهگیری {order.tracking_code} ثبت شد.")
        return redirect('orders:order_detail', pk=order.pk)
