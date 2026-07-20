from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('otp/request/', views.RequestOTPView.as_view(), name='request_otp'),
    path('otp/verify/', views.VerifyOTPView.as_view(), name='verify_otp'),
]