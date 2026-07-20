from django.urls import path
from . import views

app_name = 'profiles'

urlpatterns = [
    path('email/verify/request/', views.EmailVerificationRequestView.as_view(), name='email_verify_request'),
    path('email/verify/confirm/', views.EmailVerificationConfirmView.as_view(), name='email_verify_confirm'),
]