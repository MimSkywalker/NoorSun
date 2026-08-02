from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from .filters import filter_products
from .forms import ProductForm, ProductImageForm
from .models import Brand, Category, Product, ProductImage
from .services import (
    get_bestselling_products,
    get_discounted_products,
    get_new_products,
)


# -----------------------
# CRUD of product
# -----------------------
class ProductListView(ListView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        base_qs = Product.objects.select_related('category', 'brand') \
            .prefetch_related('images', 'variants')
        return filter_products(base_qs, self.request.GET)

    def is_ajax(self):
        return self.request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['categories'] = Category.objects.all()
        context['brands'] = Brand.objects.all()

        # Load all available product attributes dynamically.
        attributes = Attribute.objects.prefetch_related('values')
        context['attributes'] = attributes

        # Store selected values for each attribute so the UI
        # can preserve checked filters after page reload/Ajax.
        context['selected_attrs'] = {
            str(attr.id): self.request.GET.getlist(f'attr_{attr.id}')
            for attr in attributes
        }

        context['current_params'] = self.request.GET


    def render_to_response(self, context, **response_kwargs):
        if self.is_ajax():
            grid_html = render_to_string(
                'products/_product_grid.html', context, request=self.request
            )
            return JsonResponse({
                'html': grid_html,
                'is_paginated': context.get('is_paginated', False),
            })
        return super().render_to_response(context, **response_kwargs)


class ProductDetailView(DetailView):
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'

    def get_queryset(self):
        return Product.objects.select_related('category', 'brand').prefetch_related(
            'images', 'variants', 'variants__attribute_values'
        )


class ProductCreateView(CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'products/product_form.html'

    def get_success_url(self):
        messages.success(self.request, "محصول با موفقیت ساخته شد. حالا می‌تونی عکس اضافه کنی.")
        return reverse('products:image_add', kwargs={'product_id': self.object.pk})


class ProductUpdateView(UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'products/product_form.html'

    def get_success_url(self):
        messages.success(self.request, "تغییرات محصول ذخیره شد.")
        return reverse('products:detail', kwargs={'pk': self.object.pk})


class ProductDeleteView(DeleteView):
    model = Product
    template_name = 'products/product_confirm_delete.html'
    success_url = reverse_lazy('products:list')

    def form_valid(self, form):
        messages.success(self.request, "محصول حذف شد.")
        return super().form_valid(form)


# -----------------------
# Image
# -----------------------
class ProductImageCreateView(CreateView):
    model = ProductImage
    form_class = ProductImageForm
    template_name = 'products/product_image_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(Product, pk=kwargs['product_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['product'] = self.product
        return context

    def form_valid(self, form):
        form.instance.product = self.product
        messages.success(self.request, "تصویر با موفقیت اضافه شد.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('products:detail', kwargs={'pk': self.product.pk})


class ProductImageDeleteView(DeleteView):
    model = ProductImage
    template_name = 'products/product_image_confirm_delete.html'

    def get_success_url(self):
        messages.success(self.request, "تصویر حذف شد.")
        return reverse('products:detail', kwargs={'pk': self.object.product_id})


class HomeView(TemplateView):
    template_name = 'products/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['new_products'] = get_new_products()
        context['bestselling_products'] = get_bestselling_products()
        context['discounted_products'] = get_discounted_products()
        return context        