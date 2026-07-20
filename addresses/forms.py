from django import forms
from .models import Address, City


class AddressForm(forms.ModelForm):
    """
    Form for creating and updating user addresses.

    Filters the city list based on the selected province
    when the form is submitted.
    """
    class Meta:
        model = Address
        fields = ['title', 'city', 'full_address', 'postal_code', 'receiver_name', 'receiver_phone', 'is_default']
        widgets = {
            'full_address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """
        Limit the available cities to the selected province
        when the form is submitted.
        """
        province_id = self.data.get('province') if self.is_bound else None
        if province_id:
            self.fields['city'].queryset = City.objects.filter(province_id=province_id)