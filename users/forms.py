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
from django.core.exceptions import ValidationError as DjangoValidationError

User = get_user_model()


PASSWORD_ERROR_MESSAGES_FA = {
    'password_too_short': "رمز عبور خیلی کوتاه است. حداقل باید {min_length} کاراکتر باشد.",
    'password_too_common': "این رمز عبور بسیار رایج و قابل حدس است. رمز دیگری انتخاب کنید.",
    'password_entirely_numeric': "رمز عبور نباید فقط شامل عدد باشد.",
    'password_too_similar': "رمز عبور نباید شبیه به اطلاعات شخصی شما (مثل شماره موبایل) باشد.",
}

def validate_password_fa(password, user=None):
    try:
        validate_password(password, user=user)
    except DjangoValidationError as e:
        fa_messages = []
        for error in e.error_list:
            code = getattr(error, 'code', None)
            params = error.params or {}
            if code in PASSWORD_ERROR_MESSAGES_FA:
                fa_messages.append(PASSWORD_ERROR_MESSAGES_FA[code].format(**params))
            else:
                fa_messages.append(str(error.message))
        raise forms.ValidationError(fa_messages)

    
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
            validate_password_fa(p1)
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



class RegisterWithPasswordForm(forms.Form):
    phone_number = forms.CharField(max_length=11, validators=[phone_validator], label="شماره موبایل")
    password1 = forms.CharField(label="رمز عبور", widget=forms.PasswordInput)
    password2 = forms.CharField(label="تکرار رمز عبور", widget=forms.PasswordInput)

    def clean_phone_number(self):
        phone_number = self.cleaned_data['phone_number']
        if User.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError(
                "این شماره قبلاً ثبت شده است. از صفحه‌ی ورود یا ورود با OTP استفاده کنید."
            )
        return phone_number

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("رمزهای وارد شده یکسان نیستند.")
        if p1:
            validate_password_fa(p1) 
        return cleaned


class PhoneLoginForm(forms.Form):
    phone_number = forms.CharField(max_length=11, validators=[phone_validator], label="شماره موبایل")
    password = forms.CharField(label="رمز عبور", widget=forms.PasswordInput)