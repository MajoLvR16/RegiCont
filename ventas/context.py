from django.urls import NoReverseMatch, reverse

# (clave, etiqueta, url_name o None); sin url_name = deshabilitado
_ITEMS = [
    ('digitacion', 'Digitación', 'ventas:digitacion'),
    ('totales', 'Totales', 'ventas:totales'),
    ('consulta', 'Consulta', None),
    ('cubiertas', 'Cubiertas', None),
    ('promotores', 'Promotores', None),
    ('cierre', 'Cierre diario', None),
]


def navegacion(request):
    """Entrega el menú lateral; las URLs aún inexistentes resuelven a '#'."""
    menu = []
    for clave, etiqueta, url_name in _ITEMS:
        url = None
        if url_name:
            try:
                url = reverse(url_name)
            except NoReverseMatch:
                url = '#'
        menu.append({'clave': clave, 'etiqueta': etiqueta, 'url_name': url_name,
                     'url': url, 'habilitado': url_name is not None})
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated and user.tiene_permiso('administrar'):
        menu.append({'clave': 'administracion', 'etiqueta': 'Administración', 'url_name': None,
                     'url': reverse('admin:index'), 'habilitado': True})
    return {'MENU': menu}
