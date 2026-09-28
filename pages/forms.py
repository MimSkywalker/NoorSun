from django import forms

from .models import StaticPage
from .template_utils import get_custom_template_choices


class StaticPageAdminForm(forms.ModelForm):
    template_name = forms.ChoiceField(
        label='قالب اختصاصی', required=False,
        help_text="خالی = قالب پیش‌فرض (نمایش محتوای ادیتور). فایل‌های قالب را فرانت‌کار در templates/pages/custom/ می‌گذارد.",
    )

    class Meta:
        model = StaticPage
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = [('', 'قالب پیش‌فرض (نمایش محتوای ادیتور)')] + \
            get_custom_template_choices()
        current = self.instance.template_name if self.instance and self.instance.pk else ''
        if current and current not in dict(choices):
            choices.append((current, f'{current} (فایل یافت نشد!)'))
        self.fields['template_name'].choices = choices
