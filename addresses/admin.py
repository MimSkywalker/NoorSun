from django.contrib import admin
from .models import Province, City, Address


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title',)


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('title', 'province', 'slug')
    list_filter = ('province',)
    search_fields = ('title', 'province__title')
    prepopulated_fields = {'slug': ('title',)}
    autocomplete_fields = ('province',)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'city', 'receiver_name', 'is_default')
    list_filter = ('is_default', 'city__province')
    search_fields = ('user__phone_number', 'receiver_name',
                     'receiver_phone', 'full_address', 'postal_code')
    autocomplete_fields = ('user', 'city')
