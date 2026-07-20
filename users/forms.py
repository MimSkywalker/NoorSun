from django import forms
from .models import phone_validator


class PhoneNumberForm(forms.Form):
    phone_number = forms.CharField(
        max_length=11,
        validators=[phone_validator],
        label="شماره موبایل",
        widget=forms.TextInput(attrs={'placeholder': '09xxxxxxxxx'}),
    )


class OTPVerifyForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        label="کد تأیید",
        widget=forms.TextInput(
            attrs={'placeholder': '------', 'inputmode': 'numeric'}),
    )
