from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
from django.urls import reverse
from django.conf import settings


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /accounts/",      
        "Disallow: /orders/",        
        "Disallow: /profile/",       
        "Disallow: /addresses/",     
        "Disallow: /support/tickets/",  
        "Disallow: /notifications/", 
        "Disallow: /admin/",
        "",
        f"Sitemap: {settings.SITE_BASE_URL}{reverse('django.contrib.sitemaps.views.sitemap')}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")