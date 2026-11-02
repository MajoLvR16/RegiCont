from django import template

register = template.Library()


def formato_pesos(valor):
    return '$' + f'{int(valor):,}'.replace(',', '.')


register.filter('pesos', formato_pesos)
