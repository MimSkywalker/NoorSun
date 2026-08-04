from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('cart/', views.CartDetailView.as_view(), name='cart_detail'),
    path('cart/add/<int:variant_id>/', views.CartAddView.as_view(), name='cart_add'),
    path('cart/item/<int:item_id>/update/', views.CartUpdateItemView.as_view(), name='cart_update_item'),
    path('cart/item/<int:item_id>/remove/', views.CartRemoveItemView.as_view(), name='cart_remove_item'),

    path('checkout/', views.CheckoutView.as_view(), name='checkout'),

    path('', views.OrderListView.as_view(), name='order_list'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('<int:pk>/invoice/', views.OrderInvoiceView.as_view(), name='order_invoice'),
    path('<int:pk>/invoice/pdf/', views.OrderInvoicePDFView.as_view(), name='order_invoice_pdf'),
]