from django import template

register = template.Library()


@register.filter
def getlist(querydict, key):
    return querydict.getlist(key)


@register.filter
def getlist_key(querydict, attribute_id):
    return querydict.getlist(f'attr_{attribute_id}')