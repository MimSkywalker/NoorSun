from pathlib import Path

from django.conf import settings
from django.template import TemplateDoesNotExist
from django.template.loader import get_template

CUSTOM_TEMPLATE_DIR = 'pages/custom'
DEFAULT_TEMPLATE = 'pages/static_page_detail.html'


def get_custom_template_choices():
    """
    """
    choices, seen = [], set()
    for template_dir in settings.TEMPLATES[0].get('DIRS', []):
        folder = Path(template_dir) / CUSTOM_TEMPLATE_DIR
        if not folder.is_dir():
            continue
        for file in sorted(folder.glob('*.html')):
            if file.name.startswith('_'):
                continue
            name = f'{CUSTOM_TEMPLATE_DIR}/{file.name}'
            if name not in seen:
                seen.add(name)
                choices.append((name, file.name))
    return choices


def is_valid_custom_template(name):
    return name in {value for value, _label in get_custom_template_choices()}


def resolve_template(name):
    if name and name.startswith(f'{CUSTOM_TEMPLATE_DIR}/'):
        try:
            get_template(name)
            return name
        except TemplateDoesNotExist:
            pass
    return DEFAULT_TEMPLATE