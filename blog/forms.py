from django import forms

from core.forms import RecaptchaFormMixin
from .models import PostComment


class PostCommentForm(RecaptchaFormMixin, forms.ModelForm):
    recaptcha_action = 'blog_comment'

    class Meta:
        model = PostComment
        fields = ['guest_name', 'text']

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        is_authenticated = bool(user and user.is_authenticated)
        has_profile_name = False
        if is_authenticated:
            full_name = f"{user.first_name} {user.last_name}".strip()
            has_profile_name = bool(full_name)

        if is_authenticated:
            del self.fields['captcha']

            if has_profile_name:
                del self.fields['guest_name']
            else:
                self.fields['guest_name'].label = 'نام شما'
                self.fields['guest_name'].required = True
                self.fields['guest_name'].help_text = (
                    "چون در پروفایل شما نامی ثبت نشده، لطفاً نامی برای "
                    "نمایش کنار این نظر وارد کنید."
                )