from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Cart
    path('cart/', views.CartDetailView.as_view(), name='cart_detail'),
    path('cart/add/<int:variant_id>/',
         views.CartAddView.as_view(), name='cart_add'),
    path(
        'cart/item/<int:item_id>/update/',
        views.CartUpdateItemView.as_view(),
        name='cart_update_item',
    ),
    path(
        'cart/item/<int:item_id>/remove/',
        views.CartRemoveItemView.as_view(),
        name='cart_remove_item',
    ),

    # Checkout
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),

    # Payment
    path(
        'payment/fake/<int:payment_id>/',
        views.FakeGatewayView.as_view(),
        name='fake_gateway',
    ),
    path(
        'payment/callback/',
        views.PaymentCallbackView.as_view(),
        name='payment_callback',
    ),

    # Orders
    path('', views.OrderListView.as_view(), name='order_list'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('<int:pk>/pay/', views.PaymentInitiateView.as_view(),
         name='payment_initiate'),
    path('<int:pk>/cancel/', views.PaymentCancelView.as_view(),
         name='payment_cancel'),
    path('<int:pk>/invoice/', views.OrderInvoiceView.as_view(), name='order_invoice'),
    path(
        '<int:pk>/invoice/pdf/',
        views.OrderInvoicePDFView.as_view(),
        name='order_invoice_pdf',
    ),

    path('<int:order_id>/refund/request/', views.RefundRequestCreateView.as_view(), name='refund_request'),

    path('cart/discount/apply/', views.CartApplyDiscountView.as_view(), name='cart_apply_discount'),
path('cart/discount/remove/', views.CartRemoveDiscountView.as_view(), name='cart_remove_discount'),
]
