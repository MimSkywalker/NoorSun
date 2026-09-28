from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
from django.urls import reverse
from django.conf import settings


import uuid

from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.images import convert_to_webp

MAX_EDITOR_IMAGE_SIZE = 5 * 1024 * 1024

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









@staff_member_required
@require_POST
def ckeditor5_upload_image(request):
    '''
    '''
    upload = request.FILES.get('upload')
    if not upload:
        return JsonResponse({'error': {'message': 'فایلی ارسال نشده است.'}}, status=400)

    if not (upload.content_type or '').startswith('image/'):
        return JsonResponse({'error': {'message': 'فقط فایل تصویری مجاز است.'}}, status=400)

    if upload.size > MAX_EDITOR_IMAGE_SIZE:
        return JsonResponse({'error': {'message': 'حجم تصویر نباید بیش از ۵ مگابایت باشد.'}}, status=400)

    try:
        webp_file = convert_to_webp(upload, max_size=(1600, 1600))
    except Exception:
        return JsonResponse({'error': {'message': 'پردازش تصویر با خطا مواجه شد؛ فایل معتبر نیست.'}}, status=400)

    date_path = timezone.now().strftime('%Y/%m')
    path = f'editor_uploads/{date_path}/{uuid.uuid4().hex}.webp'
    saved_path = default_storage.save(path, webp_file)
    url = default_storage.url(saved_path)

    return JsonResponse({'url': url})