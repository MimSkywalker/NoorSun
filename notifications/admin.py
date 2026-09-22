from django.contrib import admin

from .models import SatisfactionSurvey


@admin.register(SatisfactionSurvey)
class SatisfactionSurveyAdmin(admin.ModelAdmin):
    list_display = ('order', 'rating', 'is_submitted', 'invitation_sent_at', 'submitted_at')
    list_filter = ('is_submitted', 'rating')
    search_fields = ('order__tracking_code',)
    readonly_fields = (
        'order', 'token', 'rating', 'comment',
        'is_submitted', 'submitted_at', 'invitation_sent_at',
    )