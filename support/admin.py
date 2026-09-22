from django.contrib import admin

from .models import FAQ, Ticket, TicketMessage


class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 1
    readonly_fields = ('created_at',)
    fields = ('sender_type', 'sender_user', 'body', 'created_at')


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('subject', 'contact_display', 'status', 'updated_at')
    list_filter = ('status',)
    search_fields = ('subject', 'user__phone_number', 'guest_phone', 'guest_email')
    readonly_fields = ('user', 'guest_name', 'guest_phone', 'guest_email', 'created_at')
    inlines = [TicketMessageInline]

    def save_formset(self, request, form, formset, change):
        """
        اگر ادمین پیامی با sender_type='admin' اضافه کند و sender_user را
        خالی بگذارد، خودکار با کاربر جاری ادمین پر می‌شود.
        """
        instances = formset.save(commit=False)
        for instance in instances:
            if instance.sender_type == TicketMessage.SenderType.ADMIN and not instance.sender_user_id:
                instance.sender_user = request.user
            instance.save()
        formset.save_m2m()


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('question', 'answer')