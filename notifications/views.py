from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from .forms import SatisfactionSurveyForm
from .models import SatisfactionSurvey


class SatisfactionSurveyView(View):
    """
    View عمومی (بدون نیاز به لاگین) — دسترسی فقط از طریق توکن امن و
    غیرقابل‌حدس در لینک، دقیقاً هم‌الگوی EmailPasswordResetConfirmView
    (فاز۲) که با uidb64/token کار می‌کرد.
    """

    def get(self, request, token):
        survey = get_object_or_404(SatisfactionSurvey, token=token)
        if survey.is_submitted:
            return render(request, 'notifications/survey_already_submitted.html', {'survey': survey})
        form = SatisfactionSurveyForm(instance=survey)
        return render(request, 'notifications/survey_form.html', {'survey': survey, 'form': form})

    def post(self, request, token):
        survey = get_object_or_404(SatisfactionSurvey, token=token)
        if survey.is_submitted:
            return render(request, 'notifications/survey_already_submitted.html', {'survey': survey})

        form = SatisfactionSurveyForm(request.POST, instance=survey)
        if form.is_valid():
            survey = form.save(commit=False)
            survey.is_submitted = True
            survey.submitted_at = timezone.now()
            survey.save()
            messages.success(request, "با تشکر از نظر شما.")
            return redirect('notifications:survey_detail', token=token)

        return render(request, 'notifications/survey_form.html', {'survey': survey, 'form': form})