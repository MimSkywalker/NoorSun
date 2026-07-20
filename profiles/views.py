from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from .forms import EmailChangeForm, EmailVerifyCodeForm
from .models import EmailVerification

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, UpdateView
from django.urls import reverse_lazy

from .models import Profile
from .forms import ProfileForm


# Session key used to store the email address
# while waiting for verification.
SESSION_PENDING_EMAIL_KEY = 'pending_verification_email'


class EmailVerificationRequestView(LoginRequiredMixin, View):
    """
    Handles email verification requests.

    Allows authenticated users to submit an email address,
    generates a verification code, and sends it by email.
    """
    template_name = 'profiles/email_verification_request.html'

    def get(self, request):
        initial = {
            'email': request.user.profile.email} if request.user.profile.email else {}
        form = EmailChangeForm(initial=initial, current_user=request.user)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = EmailChangeForm(request.POST, current_user=request.user)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        email = form.cleaned_data['email']

        try:
            verification = EmailVerification.generate(
                user=request.user, email=email)
        except ValueError as e:
            messages.error(request, str(e))
            return render(request, self.template_name, {'form': form})

        send_mail(
            subject="کد تأیید ایمیل",
            message=f"کد تأیید ایمیل شما: {verification.code}",
            from_email=None,
            recipient_list=[email],
        )

        request.session[SESSION_PENDING_EMAIL_KEY] = email
        messages.success(request, "کد تأیید به ایمیل شما ارسال شد.")
        return redirect(reverse('profiles:email_verify_confirm'))


class EmailVerificationConfirmView(LoginRequiredMixin, View):
    """
    Confirms the email verification code.

    Verifies the submitted code and marks the
    email address as verified.
    """

    template_name = 'profiles/email_verification_confirm.html'

    def get(self, request):
        if SESSION_PENDING_EMAIL_KEY not in request.session:
            return redirect(reverse('profiles:email_verify_request'))
        return render(request, self.template_name, {'form': EmailVerifyCodeForm()})

    def post(self, request):
        email = request.session.get(SESSION_PENDING_EMAIL_KEY)
        if not email:
            return redirect(reverse('profiles:email_verify_request'))

        form = EmailVerifyCodeForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        verification = (
            EmailVerification.objects
            .filter(user=request.user, email=email, is_used=False)
            .order_by('-created_at')
            .first()
        )
        if not verification:
            messages.error(request, "درخواستی یافت نشد. دوباره تلاش کنید.")
            return redirect(reverse('profiles:email_verify_request'))

        ok, error = verification.verify(form.cleaned_data['code'])
        if not ok:
            messages.error(request, error)
            return render(request, self.template_name, {'form': form})

        del request.session[SESSION_PENDING_EMAIL_KEY]
        messages.success(request, "ایمیل با موفقیت تأیید شد.")
        return redirect(reverse('profiles:detail'))


class ProfileDetailView(LoginRequiredMixin, DetailView):
    """
    Displays the authenticated user's profile.
    """
    model = Profile
    template_name = 'profiles/profile_detail.html'
    context_object_name = 'profile'

    def get_object(self, queryset=None):
        """
        Always return the logged-in user's profile.

        This prevents users from accessing other profiles
        through URL manipulation.
        """
        return self.request.user.profile


class ProfileUpdateView(LoginRequiredMixin, UpdateView):

    """
    Allows the authenticated user to update
    their own profile information.
    """
    model = Profile
    form_class = ProfileForm
    template_name = 'profiles/profile_form.html'
    success_url = reverse_lazy('profiles:detail')

    def get_object(self, queryset=None):
        """
        Return the current user's profile instead of
        looking it up by a URL parameter.
        """
        return self.request.user.profile

    def form_valid(self, form):
        """
        Displays a success message after the profile
        has been updated successfully.
        """
        messages.success(self.request, "پروفایل با موفقیت به‌روزرسانی شد.")
        return super().form_valid(form)
