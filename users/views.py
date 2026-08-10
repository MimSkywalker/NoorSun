
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate

from .forms import PhoneNumberForm, OTPVerifyForm, PhoneLoginForm, RegisterWithPasswordForm
from .models import User, OTPRequest
from .services import sms_service

from django.contrib.auth import get_user_model, REDIRECT_FIELD_NAME
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode, url_has_allowed_host_and_scheme
from django.views import View

from .forms import PhoneNumberForm, OTPVerifyForm, SetNewPasswordForm, EmailPasswordResetForm
from .models import OTPRequest
from .services import sms_service

from orders.utils import merge_guest_cart_into_user

User = get_user_model()
SESSION_LOGIN_NEXT_KEY = 'login_next_url'


def _get_safe_next_url(request, candidate):

    if candidate and url_has_allowed_host_and_scheme(
        url=candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return None


class RequestOTPView(View):
    """
    Handles the first step of phone authentication.

    The user enters a phone number and receives an OTP code.
    This flow is used for both login and registration.
    """

    template_name = 'users/request_otp.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('profiles:detail')

        next_url = _get_safe_next_url(
            request,
            request.GET.get(REDIRECT_FIELD_NAME)
        )

        if next_url:
            request.session[SESSION_LOGIN_NEXT_KEY] = next_url

        return render(
            request,
            self.template_name,
            {
                'form': PhoneNumberForm(),
                'next': next_url or '',
            }
        )

    def post(self, request):
        if request.user.is_authenticated:
            return redirect('profiles:detail')

        next_url = _get_safe_next_url(
            request,
            request.POST.get(REDIRECT_FIELD_NAME)
        )

        if next_url:
            request.session[SESSION_LOGIN_NEXT_KEY] = next_url

        form = PhoneNumberForm(request.POST)

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    'form': form,
                    'next': next_url or '',
                }
            )

        phone_number = form.cleaned_data['phone_number']

        try:
            otp = OTPRequest.generate(
                phone_number,
                purpose=OTPRequest.Purpose.REGISTER_LOGIN,
            )
        except ValueError as e:
            messages.error(request, str(e))
            return render(
                request,
                self.template_name,
                {
                    'form': form,
                    'next': next_url or '',
                }
            )

        sms_service.send_otp(phone_number, otp.code)

        request.session[SESSION_PHONE_KEY] = phone_number

        messages.success(
            request,
            "کد تأیید ارسال شد."
        )

        return redirect('users:verify_otp')


class VerifyOTPView(View):

    """
    Verifies the OTP code entered by the user.

    If the phone number belongs to an existing user, the user
    is logged in. Otherwise, a new account is created.
    """

    template_name = 'users/verify_otp.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(reverse('profiles:detail'))
        if SESSION_PHONE_KEY not in request.session:
            return redirect(reverse('users:request_otp'))
        return render(request, self.template_name, {'form': OTPVerifyForm()})

    def post(self, request):
        if request.user.is_authenticated:
            return redirect(reverse('profiles:detail'))

        phone_number = request.session.get(SESSION_PHONE_KEY)
        if not phone_number:
            return redirect(reverse('users:request_otp'))

        form = OTPVerifyForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        otp = (
            OTPRequest.objects
            .filter(phone_number=phone_number, purpose=OTPRequest.Purpose.REGISTER_LOGIN, is_used=False)
            .order_by('-created_at')
            .first()
        )

        if not otp:
            messages.error(
                request, "درخواستی برای این شماره یافت نشد. دوباره تلاش کنید.")
            return redirect(reverse('users:request_otp'))

        ok, error = otp.verify(form.cleaned_data['code'])
        if not ok:
            if otp.attempts >= otp.MAX_ATTEMPTS:
                messages.error(
                    request, "تعداد تلاش مجاز تمام شده. دوباره درخواست دهید.")
                request.session.pop(SESSION_PHONE_KEY, None)
                return redirect(reverse('users:request_otp'))
            messages.error(request, error)
            return render(request, self.template_name, {'form': form})

        user, created = User.objects.get_or_create(
            phone_number=phone_number,
            defaults={'is_phone_verified': True},
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=['password', 'is_phone_verified'])

        if not created and not user.is_phone_verified:
            user.is_phone_verified = True
            user.save(update_fields=['is_phone_verified'])

        guest_session_key = request.session.session_key
        login(request, user)
        merge_guest_cart_into_user(
            request, user, guest_session_key=guest_session_key)
        request.session.pop(SESSION_PHONE_KEY, None)

        if created:
            messages.success(request, "ثبت‌نام با موفقیت انجام شد.")
        else:
            messages.success(request, "با موفقیت وارد شدید.")
        next_url = request.session.pop(
            SESSION_LOGIN_NEXT_KEY,
            None,
        )

        if next_url:
            return redirect(next_url)

        return redirect(reverse('profiles:detail'))


# Stores the phone number used during OTP verification
SESSION_PHONE_KEY = 'otp_phone_number'

# Stores the phone number during password reset verification
SESSION_PWRESET_PHONE_KEY = 'pwreset_phone_number'

# Indicates that the phone verification step is completed
SESSION_PWRESET_VERIFIED_KEY = 'pwreset_verified_phone'


class PasswordResetChooseView(View):

    """
    Allows the user to choose the password reset method.

    The user can reset the password using:
    - SMS verification
    - Email verification
    """

    template_name = 'users/password_reset_choose.html'

    def get(self, request):
        return render(request, self.template_name)


# ---------------- SMS ----------------

class PasswordResetRequestOTPView(View):
    """
    Handles password reset requests using SMS.

    Sends an OTP code to the user's phone number
    after checking the reset request.
    """
    template_name = 'users/password_reset_request_otp.html'

    def get(self, request):
        return render(request, self.template_name, {'form': PhoneNumberForm()})

    def post(self, request):
        form = PhoneNumberForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        phone_number = form.cleaned_data['phone_number']

        if not User.objects.filter(phone_number=phone_number).exists():
            messages.success(
                request, "در صورت وجود این شماره در سیستم، کد ارسال شد.")
            return redirect(reverse('users:password_reset_verify_otp'))

        try:
            otp = OTPRequest.generate(
                phone_number, purpose=OTPRequest.Purpose.PASSWORD_RESET)
        except ValueError as e:
            messages.error(request, str(e))
            return render(request, self.template_name, {'form': form})

        sms_service.send_otp(phone_number, otp.code)
        request.session[SESSION_PWRESET_PHONE_KEY] = phone_number
        messages.success(request, "کد بازیابی ارسال شد.")
        return redirect(reverse('users:password_reset_verify_otp'))


class PasswordResetVerifyOTPView(View):
    """
    Verifies the OTP code for password reset.

    After successful verification, the user can set
    a new password.
    """
    template_name = 'users/password_reset_verify_otp.html'

    def get(self, request):
        if SESSION_PWRESET_PHONE_KEY not in request.session:
            return redirect(reverse('users:password_reset_request_otp'))
        return render(request, self.template_name, {'form': OTPVerifyForm()})

    def post(self, request):
        phone_number = request.session.get(SESSION_PWRESET_PHONE_KEY)
        if not phone_number:
            return redirect(reverse('users:password_reset_request_otp'))

        form = OTPVerifyForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        otp = (
            OTPRequest.objects
            .filter(phone_number=phone_number, purpose=OTPRequest.Purpose.PASSWORD_RESET, is_used=False)
            .order_by('-created_at')
            .first()
        )
        if not otp:
            messages.error(request, "درخواستی یافت نشد. دوباره تلاش کنید.")
            return redirect(reverse('users:password_reset_request_otp'))

        ok, error = otp.verify(form.cleaned_data['code'])
        if not ok:
            if otp.attempts >= otp.MAX_ATTEMPTS:
                messages.error(
                    request, "تعداد تلاش مجاز تمام شده. دوباره درخواست دهید.")
                request.session.pop(SESSION_PWRESET_PHONE_KEY, None)
                return redirect(reverse('users:password_reset_request_otp'))

            messages.error(request, error)
            return render(request, self.template_name, {'form': form})

        request.session.pop(SESSION_PWRESET_PHONE_KEY, None)
        request.session[SESSION_PWRESET_VERIFIED_KEY] = phone_number
        return redirect(reverse('users:password_reset_set_new'))


class PasswordResetSetNewView(View):
    """
    Allows the user to create a new password after
    successful phone verification.
    """
    template_name = 'users/password_reset_set_new.html'

    def get(self, request):
        if SESSION_PWRESET_VERIFIED_KEY not in request.session:
            return redirect(reverse('users:password_reset_request_otp'))
        return render(request, self.template_name, {'form': SetNewPasswordForm()})

    def post(self, request):
        phone_number = request.session.get(SESSION_PWRESET_VERIFIED_KEY)
        if not phone_number:
            return redirect(reverse('users:password_reset_request_otp'))

        form = SetNewPasswordForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        user = get_object_or_404(User, phone_number=phone_number)
        user.set_password(form.cleaned_data['new_password1'])
        user.save(update_fields=['password'])

        request.session.pop(SESSION_PWRESET_VERIFIED_KEY, None)

        guest_session_key = request.session.session_key
        login(request, user)
        merge_guest_cart_into_user(
            request, user, guest_session_key=guest_session_key)
        messages.success(request, "رمز عبور تغییر کرد. اکنون وارد شوید.")
        return redirect(reverse('profiles:detail'))


# ---------------- Email ----------------

class EmailPasswordResetRequestView(View):
    """
    Handles password reset requests through email.

    Generates and sends a secure password reset link.
    """
    template_name = 'users/password_reset_request_email.html'

    def get(self, request):
        return render(request, self.template_name, {'form': EmailPasswordResetForm()})

    def post(self, request):
        form = EmailPasswordResetForm(request.POST)
        if form.is_valid():
            form.send_reset_email(request)
        # همیشه به "done" هدایت می‌شه، چه ایمیل تطبیق داشته باشه چه نه —
        # جلوگیری از افشای این‌که کدام ایمیل‌ها در سیستم ثبت‌شده‌اند.
        return redirect(reverse('users:password_reset_email_done'))


class EmailPasswordResetDoneView(View):
    """
    Displays the confirmation page after sending
    the password reset email.
    """
    template_name = 'users/password_reset_email_done.html'

    def get(self, request):
        return render(request, self.template_name)


class EmailPasswordResetConfirmView(View):
    """
    Handles password reset through an email link.

    Validates the reset token and allows the user
    to set a new password.
    """
    template_name = 'users/password_reset_confirm.html'

    def _get_user(self, uidb64):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            return User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return None

    def get(self, request, uidb64, token):
        user = self._get_user(uidb64)
        if user is None or not default_token_generator.check_token(user, token):
            return render(request, self.template_name, {'valid_link': False})
        return render(request, self.template_name, {'valid_link': True, 'form': SetNewPasswordForm()})

    def post(self, request, uidb64, token):
        user = self._get_user(uidb64)
        if user is None or not default_token_generator.check_token(user, token):
            return render(request, self.template_name, {'valid_link': False})

        form = SetNewPasswordForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'valid_link': True, 'form': form})

        user.set_password(form.cleaned_data['new_password1'])
        user.save(update_fields=['password'])
        guest_session_key = request.session.session_key
        login(request, user)
        merge_guest_cart_into_user(
            request, user, guest_session_key=guest_session_key)
        messages.success(request, "رمز عبور تغییر کرد. اکنون وارد شوید.")
        return redirect(reverse('profiles:detail'))


class LogoutView(View):
    def post(self, request):
        logout(request)
        messages.success(request, "با موفقیت خارج شدید.")
        return redirect(reverse('users:request_otp'))


class RegisterWithPasswordView(View):
    template_name = 'users/register_password.html'

    def get(self, request):
        return render(request, self.template_name, {'form': RegisterWithPasswordForm()})

    def post(self, request):
        form = RegisterWithPasswordForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        user = User.objects.create_user(
            phone_number=form.cleaned_data['phone_number'],
            password=form.cleaned_data['password1'],
        )
        # چون شماره از مسیر پیامک تأیید نشده:
        user.is_phone_verified = False
        user.save(update_fields=['is_phone_verified'])

        guest_session_key = request.session.session_key
        login(request, user)
        merge_guest_cart_into_user(
            request, user, guest_session_key=guest_session_key)
        messages.success(
            request,
            "ثبت‌نام با موفقیت انجام شد. توصیه می‌شود در فرصتی مناسب شماره‌ی خود را با پیامک نیز تأیید کنید."
        )
        return redirect(reverse('profiles:detail'))


class PhoneLoginView(View):

    template_name = 'users/login_password.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('profiles:detail')

        next_url = _get_safe_next_url(
            request,
            request.GET.get(REDIRECT_FIELD_NAME)
        )

        if next_url:
            request.session[SESSION_LOGIN_NEXT_KEY] = next_url

        return render(request, self.template_name, {'form': PhoneLoginForm(), 'next': next_url or '', })

    def post(self, request):

        if request.user.is_authenticated:
            return redirect('profiles:detail')

        next_url = _get_safe_next_url(
            request,
            request.POST.get(REDIRECT_FIELD_NAME)
        )

        if next_url:
            request.session[SESSION_LOGIN_NEXT_KEY] = next_url

        form = PhoneLoginForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form, 'next': next_url or '', })

        user = authenticate(
            request,
            username=form.cleaned_data['phone_number'],
            password=form.cleaned_data['password'],
        )
        if user is None:
            messages.error(request, "شماره موبایل یا رمز عبور اشتباه است.")
            return render(request, self.template_name, {'form': form, 'next': next_url or ''})

        guest_session_key = request.session.session_key
        login(request, user)
        merge_guest_cart_into_user(
            request, user, guest_session_key=guest_session_key)
        messages.success(request, "با موفقیت وارد شدید.")
        next_url = request.session.pop(
            SESSION_LOGIN_NEXT_KEY,
            None,
        )

        if next_url:
            return redirect(next_url)
        return redirect(reverse('profiles:detail'))
