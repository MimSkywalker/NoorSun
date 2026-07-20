from django import forms
from .models import Profile


class EmailChangeForm(forms.Form):
    """
    Form for adding or changing a user's email address.

    It validates the email and ensures that it is not already
    used by another user before starting the verification process.
    """
    email = forms.EmailField(label="ایمیل")

    def __init__(self, *args, current_user=None, **kwargs):
        self.current_user = current_user
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data['email']
        qs = Profile.objects.filter(email__iexact=email)
        if self.current_user:
            qs = qs.exclude(user=self.current_user)
        if qs.exists():
            raise forms.ValidationError("این ایمیل قبلاً توسط کاربر دیگری ثبت شده است.")
        return email


class EmailVerifyCodeForm(forms.Form):
    """
    Form for verifying the email confirmation code.

    The user enters the verification code received by email
    to confirm ownership of the email address.
    """
    code = forms.CharField(
        max_length=6,
        min_length=6,
        label="کد تأیید",
        widget=forms.TextInput(attrs={'inputmode': 'numeric'}),
    )