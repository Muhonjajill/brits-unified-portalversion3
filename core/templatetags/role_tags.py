from django import template

register = template.Library()


@register.filter
def has_group(user, names):
    """{% if user|has_group:"Director" %} or {% if user|has_group:"Director,Manager" %}"""
    if not getattr(user, "is_authenticated", False):
        return False
    wanted = [n.strip() for n in names.split(",") if n.strip()]
    return user.groups.filter(name__in=wanted).exists()
