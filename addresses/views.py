from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .forms import AddressForm
from .models import Address, City


class AddressListView(LoginRequiredMixin, ListView):
    """
    Displays all addresses belonging to the
    authenticated user.
    """
    model = Address
    template_name = 'addresses/address_list.html'
    context_object_name = 'addresses'

    def get_queryset(self):
        """
        Return only the current user's addresses.
        """
        return (
            Address.objects
            .filter(user=self.request.user)
            .select_related('city', 'city__province')
            .order_by('-is_default', '-created_at')
        )


class AddressCreateView(LoginRequiredMixin, CreateView):
    """
    Allows the authenticated user
    to add a new address.
    """
    model = Address
    form_class = AddressForm
    template_name = 'addresses/address_form.html'
    success_url = reverse_lazy('addresses:list')

    def form_valid(self, form):
        """
        Assign the current user to the new address
        before saving it.
        """
        form.instance.user = self.request.user
        messages.success(self.request, "آدرس با موفقیت ثبت شد.")
        return super().form_valid(form)


class AddressUpdateView(LoginRequiredMixin, UpdateView):
    """
    Allows the authenticated user
    to update one of their addresses.
    """
    model = Address
    form_class = AddressForm
    template_name = 'addresses/address_form.html'
    success_url = reverse_lazy('addresses:list')

    def get_queryset(self):
        """
        Restrict updates to addresses owned
        by the current user.
        """
        return Address.objects.filter(user=self.request.user)

    def form_valid(self, form):
        """
        Display a success message after
        updating the address.
        """
        messages.success(self.request, "آدرس ویرایش شد.")
        return super().form_valid(form)


class AddressDeleteView(LoginRequiredMixin, DeleteView):
    """
    Allows the authenticated user
    to delete one of their addresses.
    """
    model = Address
    template_name = 'addresses/address_confirm_delete.html'
    success_url = reverse_lazy('addresses:list')

    def get_queryset(self):
        """
        Restrict deletion to addresses owned
        by the current user.
        """
        return Address.objects.filter(user=self.request.user)

    def form_valid(self, form):
        """
        Display a success message after
        deleting the address.
        """
        address = self.get_object()
        was_default = address.is_default
        user = address.user

        response = super().form_valid(form)

        if was_default:
            next_default = (
                Address.objects.filter(user=user)
                .order_by('-created_at')
                .first()
            )
            if next_default:
                next_default.is_default = True
                next_default.save()

        messages.success(self.request, "آدرس حذف شد.")
        return response



    


class AddressSetDefaultView(LoginRequiredMixin, View):
    """
    Sets one of the user's addresses
    as the default address.
    """

    def post(self, request, pk):
        """
        Mark the selected address as the default.
        """
        address = get_object_or_404(Address, pk=pk, user=request.user)
        address.is_default = True
        address.save()
        messages.success(request, "آدرس پیش‌فرض تغییر کرد.")
        return redirect(reverse_lazy('addresses:list'))


class CitiesByProvinceView(LoginRequiredMixin, View):
    """
    Returns the list of cities for the selected
    province as a JSON response.
    """

    def get(self, request, province_id):
        """
        Return all cities that belong
        to the given province.
        """
        cities = City.objects.filter(province_id=province_id).order_by(
            'title').values('id', 'title')
        return JsonResponse({'cities': list(cities)})
