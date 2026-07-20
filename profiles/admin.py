

from django.contrib import admin
from .models import Profile, EmailVerification


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'avatar', 'gender','email', 'birth_date', 'is_email_verified', 'is_completed', 'wants_promotional_sms')
    list_filter = ('gender', 'is_email_verified', 'is_completed')
    search_fields = ('user__phone_number', 'user__first_name', 'user__last_name', 'email')


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'email', 'is_used', 'created_at', 'expires_at')
    list_filter = ('is_used',)
    search_fields = ('user__phone_number', 'email')
    readonly_fields = ('code', 'created_at', 'expires_at')
    ordering = ('-created_at',)