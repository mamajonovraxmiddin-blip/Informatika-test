import base64

from django import template

register = template.Library()


@register.filter
def b64encode(value):
    if not value:
        return ""

    if isinstance(value, memoryview):
        value = value.tobytes()

    return base64.b64encode(value).decode("ascii")