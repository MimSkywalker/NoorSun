
from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from .forms import PhoneNumberForm, OTPVerifyForm
from .models import User, OTPRequest
from .services import sms_service

SESSION_PHONE_KEY = 'otp_phone_number'


class RequestOTPView(View):
    """
    گام اول: کاربر شماره موبایلش رو وارد می‌کنه.
    چه ثبت‌نام چه ورود از همین یک مسیر انجام می‌شه —
    تشخیص کاربر جدید/قدیمی در VerifyOTPView انجام می‌شه.
    """
    template_name = 'users/request_otp.html'

    def get(self, request):
        return render(request, self.template_name, {'form': PhoneNumberForm()})

    def post(self, request):
        form = PhoneNumberForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        phone_number = form.cleaned_data['phone_number']

        try:
            otp = OTPRequest.generate(phone_number, purpose=OTPRequest.Purpose.REGISTER_LOGIN)
        except ValueError as e:
            messages.error(request, str(e))
            return render(request, self.template_name, {'form': form})

        sms_service.send_otp(phone_number, otp.code)
        request.session[SESSION_PHONE_KEY] = phone_number
        messages.success(request, "کد تأیید ارسال شد.")
        return redirect(reverse('users:verify_otp'))


class VerifyOTPView(View):
    template_name = 'users/verify_otp.html'

    def get(self, request):
        if SESSION_PHONE_KEY not in request.session:
            return redirect(reverse('users:request_otp'))
        return render(request, self.template_name, {'form': OTPVerifyForm()})

    def post(self, request):
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
            messages.error(request, "درخواستی برای این شماره یافت نشد. دوباره تلاش کنید.")
            return redirect(reverse('users:request_otp'))

        ok, error = otp.verify(form.cleaned_data['code'])
        if not ok:
            messages.error(request, error)
            return render(request, self.template_name, {'form': form})

        user, created = User.objects.get_or_create(
            phone_number=phone_number,
            defaults={'is_phone_verified': True},
        )
        if not created and not user.is_phone_verified:
            user.is_phone_verified = True
            user.save(update_fields=['is_phone_verified'])

        login(request, user)
        del request.session[SESSION_PHONE_KEY]

        if created:
            messages.success(request, "ثبت‌نام با موفقیت انجام شد.")
        else:
            messages.success(request, "با موفقیت وارد شدید.")

        return redirect(reverse('profiles:detail')) 