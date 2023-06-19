from django import template
import locale

register = template.Library()

@register.filter
def add_thousands_separator(value):
    locale.setlocale(locale.LC_ALL, '')  # Set the default locale
    return locale.format_string("%.0f", value, grouping=True)

@register.filter
def convert_to_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return value