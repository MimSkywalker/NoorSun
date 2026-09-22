from django import forms

from .models import Product, ProductImage, RestockRequest, StockMovement, Review


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'title',
            'description',
            'category',
            'brand',
            'is_active',
            'slug',
            'replacement_product',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image', 'is_main', 'order']


class RestockRequestForm(forms.ModelForm):
    class Meta:
        model = RestockRequest
        fields = ['phone_number', 'email']

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('phone_number') and not cleaned_data.get('email'):
            raise forms.ValidationError(
                "حداقل یکی از شماره موبایل یا ایمیل را وارد کنید.")
        return cleaned_data


class StockMovementAdminForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = (
            'variant',
            'movement_type',
            'quantity_change',
            'note',
            'order',
        )

    def clean(self):
        cleaned_data = super().clean()

        # Validate that the requested stock movement will not result
        # in a negative stock balance before the form is submitted.
        variant = cleaned_data.get('variant')
        quantity_change = cleaned_data.get('quantity_change')

        if variant is not None and quantity_change is not None:
            # Calculate the expected stock after applying this movement.
            resulting_stock = variant.stock + quantity_change

            # Prevent stock from becoming negative and show a clear
            # validation error directly on the admin form.
            if resulting_stock < 0:
                raise forms.ValidationError(
                    f"موجودی «{variant}» نمی‌تواند منفی شود "
                    f"(موجودی فعلی={variant.stock}، "
                    f"تغییر درخواستی={quantity_change}، "
                    f"موجودی نهایی محاسبه‌شده={resulting_stock})."
                )

        return cleaned_data



class ReviewForm(forms.ModelForm):
    guest_name = forms.CharField(max_length=100, required=False, label="نام شما (برای مهمان)")

    class Meta:
        model = Review
        fields = ['rating', 'text', 'guest_name']
        widgets = {
            'rating': forms.RadioSelect(choices=Review.RATING_CHOICES),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if user and user.is_authenticated:
            self.fields['guest_name'].widget = forms.HiddenInput()
            self.fields['guest_name'].required = False

    def clean(self):
        cleaned_data = super().clean()
        if not (self.user and self.user.is_authenticated) and not cleaned_data.get('guest_name'):
            raise forms.ValidationError("برای ثبت نظر به‌عنوان مهمان، نام را وارد کنید.")
        return cleaned_data