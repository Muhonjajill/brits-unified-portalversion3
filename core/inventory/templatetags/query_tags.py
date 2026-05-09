from django import template
from django.contrib.auth.models import Group

register = template.Library()

@register.simple_tag(takes_context=True)
def query_string(context, **kwargs):
    """
    Renders the current query string with updated parameters.
    Usage: ?{% query_string page=3 %}
    """
    request = context.get('request')
    if request:
        params = request.GET.copy()
    else:
        from django.http import QueryDict
        params = QueryDict(mutable=True)
   
    for key, value in kwargs.items():
        params[key] = value
   
    return params.urlencode()

@register.simple_tag(takes_context=True)
def can_delete(context):
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return False
    user = request.user
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=['Director', 'Manager']).exists()