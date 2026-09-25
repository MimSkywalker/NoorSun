"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from products.views import HomeView



from django.contrib.sitemaps.views import sitemap
from core.sitemaps import (
    ProductSitemap, CategorySitemap, BrandSitemap,
    CampaignSitemap, FAQSitemap, StaticViewSitemap,
)
from core.views import robots_txt

sitemaps = {
    'products': ProductSitemap,
    'categories': CategorySitemap,
    'brands': BrandSitemap,
    'campaigns': CampaignSitemap,
    'faq': FAQSitemap,
    'static': StaticViewSitemap,
}


urlpatterns = [
    path('', HomeView.as_view(), name='home'),

    path('admin/', admin.site.urls),
    path('products/', include('products.urls')),
    path('accounts/', include('users.urls')),
    path('profile/', include('profiles.urls')),
    path('addresses/', include('addresses.urls')),
    path('orders/', include('orders.urls')),
    path('notifications/', include('notifications.urls')),
    path('support/', include('support.urls')),

    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt, name='robots_txt'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    import debug_toolbar
    
urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns