
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, OTPRequest


class UserAdmin(BaseUserAdmin):

    model = User
    list_display = ('phone_number', 'first_name',
                    'last_name', 'is_staff', 'is_active', 'is_phone_verified')
    list_filter = ('is_staff', 'is_active', 'is_phone_verified')
    search_fields = ('phone_number', 'first_name', 'last_name')
    ordering = ('phone_number',)

    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('اطلاعات شخصی', {'fields': ('first_name', 'last_name')}),
        ('دسترسی‌ها', {'fields': ('is_active', 'is_staff',
         'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'password1', 'password2'),
        }),
    )


admin.site.register(User, UserAdmin)


@admin.register(OTPRequest)
class OTPRequestAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'purpose', 'is_used',
                    'attempts', 'created_at', 'expires_at')
    list_filter = ('purpose', 'is_used')
    search_fields = ('phone_number',)
    readonly_fields = ('code', 'created_at', 'expires_at', 'attempts')
    ordering = ('-created_at',)
