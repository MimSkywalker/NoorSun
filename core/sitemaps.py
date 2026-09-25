from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from products.models import Product, Category, Brand, Campaign
from support.models import FAQ


class ProductSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.8

    def items(self):
        return Product.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('products:detail', kwargs={'slug': obj.slug})


class CategorySitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        return Category.objects.all()

    def location(self, obj):
        return f"{reverse('products:list')}?category={obj.slug}"


class BrandSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.5

    def items(self):
        return Brand.objects.all()

    def location(self, obj):
        return f"{reverse('products:list')}?brand={obj.slug}"


class CampaignSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.7

    def items(self):
        return [c for c in Campaign.objects.filter(is_active=True) if c.is_running]

    def location(self, obj):
        return f"{reverse('products:list')}?campaign={obj.slug}"


class FAQSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.3

    def items(self):
        return FAQ.objects.filter(is_active=True)

    def location(self, obj):
        return f"{reverse('support:faq_list')}#faq-{obj.pk}"


class StaticViewSitemap(Sitemap):
    """
   
    """
    changefreq = 'monthly'
    priority = 1.0

    def items(self):
        return ['home', 'support:faq_list', 'support:ticket_create']

    def location(self, item):
        return reverse(item)

    def priority_func(self, item):
        return 1.0 if item == 'home' else 0.4