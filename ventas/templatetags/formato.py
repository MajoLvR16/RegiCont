from django import template

register = template.Library()


def formato_pesos(valor):
    return '$' + f'{int(valor):,}'.replace(',', '.')


register.filter('pesos', formato_pesos)


def pesos_con_signo(valor):
    valor = int(valor)
    return ('−' if valor < 0 else '') + formato_pesos(abs(valor))


register.filter('pesos_con_signo', pesos_con_signo)
