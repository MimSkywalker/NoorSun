from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('otp/request/', views.RequestOTPView.as_view(), name='request_otp'),
    path('otp/verify/', views.VerifyOTPView.as_view(), name='verify_otp'),

    path('password-reset/', views.PasswordResetChooseView.as_view(), name='password_reset_choose'),

    # SMS
    path('password-reset/otp/', views.PasswordResetRequestOTPView.as_view(), name='password_reset_request_otp'),
    path('password-reset/otp/verify/', views.PasswordResetVerifyOTPView.as_view(), name='password_reset_verify_otp'),
    path('password-reset/otp/set-new/', views.PasswordResetSetNewView.as_view(), name='password_reset_set_new'),

    # Email
    path('password-reset/email/', views.EmailPasswordResetRequestView.as_view(), name='password_reset_email_request'),
    path('password-reset/email/done/', views.EmailPasswordResetDoneView.as_view(), name='password_reset_email_done'),
    path('password-reset/email/confirm/<uidb64>/<token>/', views.EmailPasswordResetConfirmView.as_view(), name='password_reset_confirm'),

    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('register-password/', views.RegisterWithPasswordView.as_view(), name='register_password'),
path('login-password/', views.PhoneLoginView.as_view(), name='login_password'),
]