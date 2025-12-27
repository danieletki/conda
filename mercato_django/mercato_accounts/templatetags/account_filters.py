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
