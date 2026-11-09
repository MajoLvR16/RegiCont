from django.urls import NoReverseMatch, reverse

# (clave, etiqueta, url_name o None); sin url_name = deshabilitado
_ITEMS = [
    ('digitacion', 'Digitación', 'ventas:digitacion'),
    ('totales', 'Totales', 'ventas:totales'),
    ('consulta', 'Consulta', 'ventas:consulta'),
    ('cubiertas', 'Cubiertas', 'ventas:cubiertas'),
    ('promotores', 'Promotores', None),
    ('cierre', 'Cierre diario', None),
]


def navegacion(request):
    """Entrega el menú lateral; las URLs aún inexistentes resuelven a '#'."""
    user = getattr(request, 'user', None)
    menu = []
    for clave, etiqueta, url_name in _ITEMS:
        # Cubiertas solo aparece a quien tiene el permiso.
        if clave == 'cubiertas' and not (user is not None and user.is_authenticated
                                         and user.tiene_permiso('cubiertas')):
            continue
        url = None
        if url_name:
            try:
                url = reverse(url_name)
            except NoReverseMatch:
                url = '#'
        menu.append({'clave': clave, 'etiqueta': etiqueta, 'url_name': url_name,
                     'url': url, 'habilitado': url_name is not None})
    if user is not None and user.is_authenticated and user.tiene_permiso('administrar'):
        menu.append({'clave': 'administracion', 'etiqueta': 'Administración', 'url_name': None,
                     'url': reverse('admin:index'), 'habilitado': True})
    return {'MENU': menu}
