from django.urls import path

from . import views

app_name = 'support'

urlpatterns = [
    path('contact/', views.TicketCreateView.as_view(), name='ticket_create'),
    path('contact/sent/<int:pk>/', views.TicketCreatedView.as_view(), name='ticket_created'),
    path('tickets/', views.TicketListView.as_view(), name='ticket_list'),
    path('tickets/<int:pk>/', views.TicketDetailView.as_view(), name='ticket_detail'),
    path('faq/', views.FAQListView.as_view(), name='faq_list'),
]