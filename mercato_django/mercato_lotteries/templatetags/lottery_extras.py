import base64
from django import template

register = template.Library()

@register.filter
def base64(image_data):
    """
    Convert binary image data to base64 string for use in img src
    """
    if not image_data:
        return ""
    
    try:
        encoded = base64.b64encode(image_data).decode('ascii')
        return encoded
    except Exception:
        return ""