from django import forms
from .models import phone_validator


from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

User = get_user_model()

class PhoneNumberForm(forms.Form):

    """
    Form for collecting the user's phone number.

    The phone number is validated using a custom validator
    to ensure that only valid mobile numbers are accepted.
    """

    phone_number = forms.CharField(
        max_length=11,
        validators=[phone_validator],
        label="شماره موبایل",
        widget=forms.TextInput(attrs={'placeholder': '09xxxxxxxxx'}),
    )


class OTPVerifyForm(forms.Form):
    """
    Form for verifying a one-time password (OTP).

    The user enters the code received via SMS.
    This form validates the basic structure and length of the code.
    """

    code = forms.CharField(
        max_length=6,
        min_length=6,
        label="کد تأیید",
        widget=forms.TextInput(
            attrs={'placeholder': '------', 'inputmode': 'numeric'}),
    )


class SetNewPasswordForm(forms.Form):
    """
    Form for setting a new password after successful verification.

    This form is shared between:
    - SMS-based password recovery
    - Email-based password recovery

    It validates password confirmation and applies Django's
    built-in password validation rules.
    """   
    new_password1 = forms.CharField(label="رمز عبور جدید", widget=forms.PasswordInput)
    new_password2 = forms.CharField(label="تکرار رمز عبور جدید", widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('new_password1'), cleaned.get('new_password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("رمزهای وارد شده یکسان نیستند.")
        if p1:
            validate_password(p1)
        return cleaned


class EmailPasswordResetForm(forms.Form):
    """
    Form for requesting password reset through email.

    Only users who have:
    - A unique email address in their profile
    - A verified email address
    - An active account

    are allowed to use this recovery method.
    """
    email = forms.EmailField(label="ایمیل")

    def get_matching_users(self):
        """
        Returns users matching the provided email address
        and meeting the required password reset conditions.
        """
    
        email = self.cleaned_data['email']
        return User.objects.filter(
            profile__email__iexact=email,
            profile__is_email_verified=True,
            is_active=True,
        )

    def send_reset_email(self, request):
        """
        Generates secure password reset links and sends them via email.

        For each matching user:
        - Creates an encoded user ID.
        - Generates a temporary reset token.
        - Builds the reset URL.
        - Sends the reset email.
        """        
        for user in self.get_matching_users():
            if not user.has_usable_password():
                continue
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = request.build_absolute_uri(
                reverse('users:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            )
            message = render_to_string('users/password_reset_email.txt', {
                'user': user, 'reset_link': reset_link,
            })
            send_mail(
                subject="بازیابی رمز عبور",
                message=message,
                from_email=None,
                recipient_list=[self.cleaned_data['email']],
            )