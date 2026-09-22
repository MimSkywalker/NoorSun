from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.db import models
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from .filters import filter_products
from .forms import ProductForm, ProductImageForm, RestockRequestForm, ReviewForm
from .models import (
    Attribute,
    Brand,
    Category,
    Product,
    ProductImage,
    Campaign,
    RestockRequest,
    ProductVariant,
    Review)

from .services import (
    get_bestselling_products,
    get_discounted_products,
    get_new_products,
    get_similar_products,
    attach_campaign_prices,
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
        context['products'] = attach_campaign_prices(context['products'])

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

        campaign_slug = self.request.GET.get('campaign')
        if campaign_slug:
            context['active_campaign'] = Campaign.objects.filter(
                slug=campaign_slug, is_active=True
            ).first()
        return context

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['similar_products'] = attach_campaign_prices(
            get_similar_products(self.object))
        context['is_unavailable'] = not self.object.is_active
        context['approved_reviews'] = self.object.reviews.filter(is_approved=True).select_related('user')
        return context


class ProductCreateView(CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'products/product_form.html'

    def get_success_url(self):
        messages.success(
            self.request, "محصول با موفقیت ساخته شد. حالا می‌تونی عکس اضافه کنی.")
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
        context['new_products'] = attach_campaign_prices(get_new_products())
        context['bestselling_products'] = attach_campaign_prices(
            get_bestselling_products())
        context['discounted_products'] = attach_campaign_prices(
            get_discounted_products())

        now = timezone.now()
        context['active_campaigns'] = Campaign.objects.filter(
            is_active=True, start_at__lte=now, end_at__gte=now
        ).order_by('end_at')[:4]

        return context


class CampaignListView(ListView):
    model = Campaign
    template_name = 'products/campaign_list.html'
    context_object_name = 'campaigns'
    paginate_by = 12

    def get_queryset(self):
        now = timezone.now()
        # Just active Campaigns
        return Campaign.objects.filter(
            is_active=True, start_at__lte=now, end_at__gte=now
        ).order_by('end_at')


class RestockRequestCreateView(CreateView):
    model = RestockRequest
    form_class = RestockRequestForm
    template_name = 'products/restock_request_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.variant = get_object_or_404(
            ProductVariant, pk=kwargs['variant_id'])
        if self.variant.stock > 0:
            messages.info(request, "این کالا در حال حاضر موجود است.")
            return redirect('products:detail', pk=self.variant.product_id)
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        if self.request.user.is_authenticated:
            initial['phone_number'] = self.request.user.phone_number
            if self.request.user.profile.email:
                initial['email'] = self.request.user.profile.email
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['variant'] = self.variant
        return context

    def form_valid(self, form):
        form.instance.variant = self.variant
        if self.request.user.is_authenticated:
            form.instance.user = self.request.user

        already_requested = RestockRequest.objects.filter(
            variant=self.variant,
            is_notified=False,
            phone_number=form.instance.phone_number,
        ).exists()
        if already_requested and form.instance.phone_number:
            messages.info(
                self.request, "شما قبلاً برای این کالا درخواست ثبت کرده‌اید.")
            return redirect('products:detail', pk=self.variant.product_id)

        messages.success(
            self.request,
            "درخواست شما ثبت شد؛ به‌محض موجود شدن این کالا به شما اطلاع می‌دهیم."
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('products:detail', kwargs={'pk': self.variant.product_id})


class ReviewCreateView(CreateView):
    model = Review
    form_class = ReviewForm
    template_name = 'products/review_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(Product, pk=kwargs['product_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        instance = Review(product=self.product)
        if self.request.user.is_authenticated:
            instance.user = self.request.user
        kwargs['instance'] = instance
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['product'] = self.product
        return context

    def form_valid(self, form):
        if self.request.user.is_authenticated:
            form.instance.guest_name = ''
        messages.success(
            self.request,
            "نظر شما ثبت شد و پس از بررسی و تأیید مدیر نمایش داده خواهد شد."
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('products:detail', kwargs={'pk': self.product.pk})
