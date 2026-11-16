# Iteración 3 – RegiCont

## 1. Alcance

| Historia de usuario | Requerimientos |
|---|---|
| HU-05 Informe de Cierre Diario | RF10 Exportación e impresión del informe de cierre |
| Correcciones de la revisión de capturas (Iteración 2) | Seis correcciones menores, descritas en la sección 4 |

Roles: Operador y Administrador. El ítem "Cierre diario" del menú queda activo para ambos (antes figuraba como "Próximamente").

## 2. Trazabilidad

| RF / corrección | Implementación | Pruebas automáticas (`ventas/tests/`) |
|---|---|---|
| RF10 Informe de cierre diario (pantalla) | `ventas/services.py` (`CierreService.informe`), `ventas/forms.py` (`FormularioCierre`), `ventas/views/cierre.py` (`CierreController.Pantalla`), `ventas/templates/cierre/cierre.html` | `test_cierre.py` |
| RF10 Impresión | `ventas/views/cierre.py` (`CierreController.Imprimir`), `ventas/templates/cierre/imprimir.html`, `ventas/urls.py` (`/cierre/imprimir/`) | `test_cierre.py` |
| RF10 Exportación CSV | `ventas/services.py` (`CierreService.generar_csv`), `ventas/views/cierre.py` (`CierreController.ExportarCsv`), `ventas/urls.py` (`/cierre/exportar/`) | `test_cierre.py` |
| Menú y permiso `cierre` (ambos roles) | `ventas/models.py` (`Usuario.PERMISOS`), `ventas/context.py`, `ventas/urls.py` | `test_cierre.py`, `test_admin.py` |
| Corrección 1: páginas 403 y 404 en español | `ventas/templates/403.html`, `ventas/templates/404.html` | `test_errores.py` |
| Corrección 2: ayuda del rol actualizada | `ventas/admin.py` | `test_admin.py` |
| Corrección 3: selector de rol del admin sin recorte | `ventas/static/css/admin_regicont.css` | Sin prueba automática: se verificó en el navegador |
| Corrección 4: topes registrados ordenados por valor numérico | `ventas/views/cubiertas.py` | `test_cubiertas.py` |
| Corrección 5: paginación de Consulta oculta con una sola página | `ventas/templates/consulta/consulta.html` | `test_consulta.py` |
| Corrección 6: atajos de monto con formato de pesos | `ventas/static/js/digitacion.js` | Sin prueba automática: se verificó en el navegador |

## 3. Arquitectura

```
Usuario → Vista → Controlador → Servicio → Modelo → BD
```

Mismo flujo de las iteraciones anteriores. Se agregan:

- Servicio (`ventas/services.py`): `CierreService` con `informe` y `generar_csv`.
- Controlador (`ventas/views/cierre.py`): `CierreController` con `Pantalla`, `Imprimir` y `ExportarCsv`.
- Permiso `cierre` en `Usuario.PERMISOS` para Administrador y Operador.
- Plantillas nuevas: `ventas/templates/cierre/cierre.html` y `ventas/templates/cierre/imprimir.html`.
- Sin migraciones en esta iteración: el informe se calcula sobre `Jugada`.

## 4. Ajustes al diseño

| Diseño original | Ajuste | Justificación |
|---|---|---|
| RF10 "exportar o imprimir" sin formato definido | Impresión en una vista propia (`/cierre/imprimir/`), tamaño carta con `@media print`; el botón Imprimir no aparece en la hoja impresa y el navegador permite "Guardar como PDF". Exportación CSV en UTF-8 con BOM, separador punto y coma, montos enteros con encabezado "Monto (COP)", archivo `cierre_AAAA-MM-DD.csv`. | No se agregan librerías nuevas (RE3). Excel muestra las tildes y puede sumar los montos. |
| Contenido del informe: "totales por promotor y números de mayor recaudo" | Totales por promotor con fila de total y los 30 números de mayor recaudo (en impresión, dos tablas de 15). | Cabe en una página carta incluso un sábado. |
| Jornada sin registros | Aviso "No hay datos para generar el informe de la fecha seleccionada"; no se imprime ni se exporta. | Evita informes vacíos. |
| Fecha del informe | No se permiten fechas futuras. | Una jornada futura no tiene datos. |
| Páginas 403 y 404 de Django | Páginas propias en español (antes "403 Forbidden" y "Not Found"). | Coherencia con el resto de la aplicación. |
| Ayuda del rol en el admin | Actualizada: Operador: Digitación, Totales, Consulta y Cierre diario. | Refleja el nuevo permiso. |
| Selector de rol del admin | Sin recorte: `height: auto` en `select` frente a la altura fija de 30 px del CSS del admin, que no cabía con letra de 16 px. | El texto del selector se veía cortado. |
| Topes registrados en Cubiertas | Ordenados por valor numérico (`Cast` a entero) y no como texto. | Con orden de texto, 1028 quedaba antes que 318. |
| Paginación de Consulta | Se oculta cuando hay una sola página. | Los controles no aportan nada con una página. |
| Atajos de monto en Digitación | Muestran "$10.000"; la validación ignora el "$" y los puntos. | Formato de pesos consistente con el resto de la pantalla. |

**Limitación conocida:** en el CSV, Excel puede quitar los ceros a la izquierda de números como 0742 al abrir el archivo.

## 5. Pruebas automáticas

Todas pasan. Comando: `python manage.py test -v 2` sobre `main`, 16/11/2026. Resultado: `Ran 175 tests in 101.401s` y `OK`.

| Archivo (`ventas/tests/`) | Qué cubre | Pruebas |
|---|---|---|
| `test_acceso.py` | Ingreso, salida, redirección de anónimos, permisos por rol, menú de Administración y acceso concurrente. | 12 |
| `test_admin.py` | Acceso al admin solo para Administrador, formularios de Usuario, contraseñas, solo lectura de Jugadas y Totales, sin borrar y ayuda del rol. | 14 |
| `test_base.py` | Zona horaria, renderizado de plantillas base, menú y logo. | 4 |
| `test_cierre.py` (nuevo) | Totales, orden de promotores y fila total, 30 números de mayor recaudo, ceros a la izquierda, aislamiento por fecha, encabezado, jornada sin datos, permisos y menú, CSV, fecha futura o inválida, plantilla de impresión y rendimiento. | 16 |
| `test_comandos.py` | Comandos `cargar_datos_iniciales` y `generar_datos_prueba` (modos, idempotencia, rendimiento de totales). | 8 |
| `test_consulta.py` | Acceso por rol, aislamiento por fecha, filtro por promotor, búsqueda por número (ceros), paginación (con controles solo si hay más de una página) y rendimiento (RNF02). | 22 |
| `test_cubiertas.py` | Registro y actualización de topes y sus validaciones, orden numérico de topes, reporte, detalle por promotor, permisos y rendimiento. | 30 |
| `test_digitacion.py` | Pantalla de Digitación sin lotería, atajos de valor, registro por POST, errores, CSRF y jugadas de hoy. | 12 |
| `test_errores.py` (nuevo) | Páginas 403 y 404 en español, con enlace "Volver al inicio" y menú lateral. | 2 |
| `test_modelos.py` | Validaciones de `Jugada`, acumulación de `TotalNumero`, `Promotor`, roles de `Usuario` y admin. | 13 |
| `test_promotores.py` | Alta, edición y validaciones del catálogo, activar y desactivar, rechazo de inactivos en digitación, listado, permisos y admin sin Promotores. | 24 |
| `test_servicios.py` | `RegistroJugadaService`: fecha y hora de Caracas, acumulación, errores, transacción, token repetido y concurrencia de 8 hilos. | 11 |
| `test_totales.py` | Consolidado: orden, total, aislamiento por fecha, suma entre promotores, textos y rendimiento. | 7 |
| **Total** | | **175** |

## 6. Rendimiento medido

Medición del 16/11/2026 con 2.535 jugadas por $14.000.000.

**Método:** igual que en la iteración 2: `runserver` local en 127.0.0.1, cliente HTTP con sesión de Operador, 1 solicitud de calentamiento y 20 medidas por ruta.

**Equipo:** Intel Core i5-10300H 2,50 GHz, 7,8 GB de RAM, SSD, Windows 11 Home; Python 3.13.3, Django 5.2.18, SQLite 3.49.1. No es el entorno de producción.

| Ruta | Mediana (s) | Mín. (s) | Máx. (s) | RNF02 (< 2 s) |
|---|---|---|---|---|
| `/cierre/` | 0,013 | 0,012 | 0,015 | Cumple |
| `/cierre/imprimir/` | 0,012 | 0,011 | 0,014 | Cumple |
| `/cierre/exportar/` | 0,010 | 0,009 | 0,011 | Cumple |
| `/cierre/` sin datos | 0,007 | 0,007 | 0,010 | Cumple |

## 7. Páginas del informe impreso

Medido con Playwright (Chromium, `page.pdf` en tamaño carta, con `media print`):

| Jornada | Páginas |
|---|---|
| Sábado de 2.535 jugadas | 1 |
| Jornada de 8 jugadas | 1 |

## 8. Pendientes

- Pruebas y despliegue en PostgreSQL: no se han ejecutado en ese motor.
- Prueba con dos operadores reales en equipos distintos.
- Prueba de corte real de luz.
- Navegadores antiguos (RE3): sin verificar.
- Límite de intentos de ingreso: hoy no existe.
- Impresión real en la impresora de la oficina: solo se verificó el PDF.
- Comportamiento del CSV en la versión de Excel de la oficina.
- La página de Cubiertas lista todos los números del día sin paginar.
