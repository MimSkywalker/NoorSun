from django import forms

from .models import Product, ProductImage


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