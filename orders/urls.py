from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('cart/', views.CartDetailView.as_view(), name='cart_detail'),
    path('cart/add/<int:variant_id>/', views.CartAddView.as_view(), name='cart_add'),
    path('cart/item/<int:item_id>/update/', views.CartUpdateItemView.as_view(), name='cart_update_item'),
    path('cart/item/<int:item_id>/remove/', views.CartRemoveItemView.as_view(), name='cart_remove_item'),
]