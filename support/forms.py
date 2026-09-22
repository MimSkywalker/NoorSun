from django import forms

from .models import Ticket, TicketMessage
from core.forms import RecaptchaFormMixin

class TicketCreateForm(RecaptchaFormMixin, forms.ModelForm):
    message = forms.CharField(widget=forms.Textarea, label="متن پیام")

    class Meta:
        model = Ticket
        fields = ['subject', 'guest_name', 'guest_phone', 'guest_email', 'message']

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if user and user.is_authenticated:
            for field in ('guest_name', 'guest_phone', 'guest_email'):
                self.fields[field].widget = forms.HiddenInput()
                self.fields[field].required = False

    def clean(self):
        cleaned_data = super().clean()
        if not (self.user and self.user.is_authenticated):
            if not (cleaned_data.get('guest_phone') or cleaned_data.get('guest_email')):
                raise forms.ValidationError("حداقل شماره موبایل یا ایمیل را وارد کنید.")
        return cleaned_data


class TicketMessageForm(forms.ModelForm):
    class Meta:
        model = TicketMessage
        fields = ['body']