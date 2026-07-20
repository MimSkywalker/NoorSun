# URL patterns for address management.

from django.urls import path
from . import views

app_name = 'addresses'

urlpatterns = [
    path('', views.AddressListView.as_view(), name='list'),
    path('add/', views.AddressCreateView.as_view(), name='create'),
    path('<int:pk>/edit/', views.AddressUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.AddressDeleteView.as_view(), name='delete'),
    path('<int:pk>/set-default/', views.AddressSetDefaultView.as_view(), name='set_default'),
    path('ajax/cities/<int:province_id>/', views.CitiesByProvinceView.as_view(), name='ajax_cities'),
]