from django.views.generic import DetailView

from .models import StaticPage
from .template_utils import resolve_template


class StaticPageDetailView(DetailView):
    model = StaticPage
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    context_object_name = 'page'

    def get_queryset(self):
        return StaticPage.objects.filter(is_active=True)

    def get_template_names(self):
        return [resolve_template(self.object.template_name)]