from django import forms
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV3


class RecaptchaFormMixin(forms.Form):
    """
   
    """
    recaptcha_action = 'generic'

    captcha = ReCaptchaField(
        widget=ReCaptchaV3(attrs={'required_score': 0.5}),
        label='',
        error_messages={'required': 'لطفاً چند لحظه صبر کنید و دوباره تلاش کنید.'},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['captcha'].widget.attrs['action'] = self.recaptcha_action