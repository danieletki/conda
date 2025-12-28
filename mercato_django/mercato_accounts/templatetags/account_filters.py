from django import template

register = template.Library()

@register.filter(name='split')
def split(value, arg):
    """
    Splits the string by the given separator.
    Usage: {{ value|split:"," }}
    """
    if not value:
        return []
    return value.split(arg)


@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Gets an item from a dictionary by key.
    Usage: {{ dictionary|get_item:key }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)
