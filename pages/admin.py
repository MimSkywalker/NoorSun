from django.contrib import admin
from django.utils.html import format_html

from .models import Slide, StaticPage
from django import forms
from .template_utils import get_custom_template_choices
from .forms import StaticPageAdminForm
@admin.register(Slide)
class SlideAdmin(admin.ModelAdmin):
    list_display = ('thumbnail', 'title', 'order', 'is_active', 'start_at', 'end_at', 'is_visible_now')
    list_display_links = ('thumbnail', 'title')
    list_editable = ('order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title', 'subtitle')
    readonly_fields = ('thumbnail', 'thumbnail_mobile')
    fieldsets = (
        ('محتوا', {'fields': ('title', 'subtitle', 'button_text', 'link_url')}),
        ('تصاویر', {'fields': ('image', 'thumbnail', 'image_mobile', 'thumbnail_mobile', 'image_alt')}),
        ('نمایش', {'fields': ('order', 'is_active', 'start_at', 'end_at')}),
    )

    @admin.display(description='پیش‌نمایش')
    def thumbnail(self, obj):
        if obj.pk and obj.image:
            return format_html('<img src="{}" style="height:50px;border-radius:4px;">', obj.image.url)
        return '—'

    @admin.display(description='پیش‌نمایش موبایل')
    def thumbnail_mobile(self, obj):
        if obj.pk and obj.image_mobile:
            return format_html('<img src="{}" style="height:50px;border-radius:4px;">', obj.image_mobile.url)
        return '—'

    @admin.display(boolean=True, description='در حال نمایش؟')
    def is_visible_now(self, obj):
        return obj.is_visible_now


@admin.register(StaticPage)
class StaticPageAdmin(admin.ModelAdmin):
    form = StaticPageAdminForm
    list_display = ('title', 'slug', 'template_name', 'is_active', 'show_in_menu',
                    'show_in_footer', 'include_in_sitemap', 'order')
    fieldsets = (
        (None, {'fields': ('title', 'title_en', 'slug', 'template_name', 'content')}),
        ('نمایش', {'fields': ('is_active', 'show_in_menu', 'show_in_footer', 'order')}),
        ('سئو', {'fields': ('meta_title', 'meta_description', 'include_in_sitemap')}),
    )
    list_editable = ('is_active', 'show_in_menu', 'show_in_footer', 'order')
    list_filter = ('is_active', 'show_in_menu', 'show_in_footer')
    search_fields = ('title', 'title_en', 'slug')
    