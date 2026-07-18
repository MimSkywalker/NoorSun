from django.contrib import admin
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'avatar', 'gender',
                    'birth_date', 'wants_promotional_sms')
    search_fields = ('user__phone_number',
                     'user__first_name', 'user__last_name')
