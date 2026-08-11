from django import forms


class DiscountCodeForm(forms.Form):
    code = forms.CharField(max_length=30, label="کد تخفیف")