# Iteración 2 – RegiCont

## 1. Alcance

| Historia de usuario | Requerimientos |
|---|---|
| CR-02 Retiro de la lotería (Acta No. 02, 27/10/2026) | Afecta RF02, RF05, RF06 y RF12 |
| HU-03 Consulta Histórica por Fecha, Promotor y Lotería | RF05 Consulta estricta por fecha (aislamiento), RF06 Filtrado por promotor (sin lotería tras CR-02), RF07 Búsqueda directa por número de apuesta |
| HU-04 Control de Cubiertas | RF09 Reporte de trazabilidad y cobertura frente a los límites, RF13 Registro y actualización de topes de cubierta |
| HU-07 Gestión del Catálogo de Promotores | RF12 Módulo de catálogo de promotores y comisiones |

Menú: Consulta se muestra a ambos roles; Cubiertas y Promotores solo al Administrador (el Operador no los ve). Cierre diario sigue como "Próximamente" y se construirá en la iteración 3.

## 2. Trazabilidad

| RF | Implementación | Pruebas automáticas (`ventas/tests/`) |
|---|---|---|
| CR-02 Retiro de la lotería | `ventas/migrations/0003_sin_loteria.py`, `ventas/models.py`, `ventas/services.py`, `ventas/templates/jugadas/digitacion.html`, `ventas/static/js/digitacion.js`, `ventas/admin.py`, `ventas/management/commands/cargar_datos_iniciales.py` | `test_digitacion.py`, `test_servicios.py`, `test_comandos.py`, `test_admin.py` |
| RF05 Consulta estricta por fecha | `ventas/services.py` (`ConsultaService.filtrar_por_fecha`, `consultar`), `ventas/forms.py` (`FormularioConsulta`), `ventas/views/consulta.py`, `ventas/templates/consulta/consulta.html` | `test_consulta.py` |
| RF06 Filtrado por promotor | `ventas/services.py` (`ConsultaService.filtrar_por_promotor`), `ventas/forms.py`, `ventas/views/consulta.py`, `ventas/templates/consulta/consulta.html` | `test_consulta.py` |
| RF07 Búsqueda directa por número | `ventas/services.py` (`ConsultaService.buscar_por_numero`), `ventas/forms.py`, `ventas/views/consulta.py`, `ventas/templates/consulta/consulta.html` | `test_consulta.py` |
| RF09 Reporte de trazabilidad y cobertura | `ventas/services.py` (`CubiertaService.reporte`, `aportes`), `ventas/views/cubiertas.py`, `ventas/templates/cubiertas/cubiertas.html`, `ventas/templates/cubiertas/detalle.html` | `test_cubiertas.py` |
| RF12 Catálogo de promotores y comisiones | `ventas/models.py` (`Promotor.activo`), `ventas/migrations/0005_promotor_activo.py`, `ventas/services.py` (`PromotorService`, rechazo de inactivos en `RegistroJugadaService`), `ventas/views/promotores.py`, `ventas/templates/promotores/listado.html`, `ventas/templates/promotores/formulario.html` | `test_promotores.py`, `test_digitacion.py` |
| RF13 Registro y actualización de topes | `ventas/models.py` (`TopeCubierta`), `ventas/migrations/0004_tope_cubierta.py`, `ventas/services.py` (`CubiertaService.registrar_tope`), `ventas/views/cubiertas.py` | `test_cubiertas.py` |
| Menú y permisos por rol (HU-03, HU-04, HU-07) | `ventas/context.py`, `ventas/models.py` (`Usuario.PERMISOS`), `ventas/permisos.py`, `ventas/urls.py` | `test_acceso.py`, `test_consulta.py`, `test_cubiertas.py`, `test_promotores.py`, `test_base.py` |

## 3. Arquitectura

```
Usuario → Vista → Controlador → Servicio → Modelo → BD
```

Mismo flujo de la iteración 1. Se agregan:

- Controladores (`ventas/views/`): `ConsultaController`, `CubiertaController` y `PromotorController`.
- Servicios (`ventas/services.py`): `ConsultaService`, `CubiertaService` y `PromotorService`.
- Modelos: se agrega `TopeCubierta` y se retira `Loteria`; `Promotor` incorpora el campo `activo`.
- Plantillas nuevas: `ventas/templates/consulta/`, `ventas/templates/cubiertas/` y `ventas/templates/promotores/`.

## 4. Ajustes al diseño del FP15

Sección 2.1 del FP15.

| Diseño original | Ajuste | Justificación |
|---|---|---|
| `LOTERIA` y `JUGADA.id_loteria` | Retirados del modelo, la pantalla de Digitación, los servicios, la administración y los datos iniciales (migración `0003_sin_loteria`). | CR-02 aprobado por la cliente: la lotería no se usa en la operación y la digitación resulta más rápida. |
| `PROMOTOR` sin campo de estado | Nuevo campo `activo` (booleano, verdadero por defecto; migración `0005_promotor_activo`). | RF12 pide no borrar promotores. Un promotor inactivo no se puede digitar y conserva sus jugadas. |
| `TOPE_CUBIERTA` (`numero` PK, `monto_tope` > 0, `id_usuario`, `fecha_actualizacion`) | Implementada igual (migración `0004_tope_cubierta`), con validación de 3 o 4 cifras, monto mayor que cero, restricción en la BD y `fecha_actualizacion` automática. | Cumple RF13 con las reglas del FP15 garantizadas también por la base de datos. |
| Índices `JUGADA(fecha)`, `(fecha, numero)` y `(fecha, codigo_promotor)` | Se mantienen desde la iteración 1 (migración `0001_initial`). | Los usan Consulta y Cubiertas. |
| RF06 "por promotor y lotería" | Solo por promotor. | Consecuencia de CR-02. |
| Catálogo de promotores en el admin de Django (iteración 1) | Pantalla propia en `/promotores/`; el admin queda solo con Usuarios (y Jugadas y Totales de solo lectura). | RF12 / HU-07. |

**Otras precisiones:**

- RF07 busca el número dentro de la fecha seleccionada.
- Consulta pagina de a 100 jugadas.
- Cubiertas: diferencia = tope − recaudado; un recaudado igual al tope no lo supera.
- Los topes valen para cualquier fecha.

## 5. Pruebas automáticas

Todas pasan. Comando: `python manage.py test -v 2` sobre `main`, 09/11/2026. Resultado: `Ran 153 tests in 105.923s` y `OK`.

| Archivo (`ventas/tests/`) | Qué cubre | Pruebas |
|---|---|---|
| `test_acceso.py` | Ingreso, salida, redirección de anónimos, permisos por rol, menú de Administración y acceso concurrente. | 12 |
| `test_admin.py` | Acceso al admin solo para Administrador, formularios de Usuario, contraseñas, solo lectura de Jugadas y Totales, sin borrar. | 13 |
| `test_base.py` | Zona horaria, renderizado de plantillas base, menú y logo. | 4 |
| `test_comandos.py` | Comandos `cargar_datos_iniciales` y `generar_datos_prueba` (modos, idempotencia, rendimiento de totales). | 8 |
| `test_consulta.py` | Acceso por rol, aislamiento por fecha, filtro por promotor, búsqueda por número (ceros), paginación y rendimiento (RNF02). | 20 |
| `test_cubiertas.py` | Registro y actualización de topes y sus validaciones, reporte, detalle por promotor, permisos y rendimiento. | 29 |
| `test_digitacion.py` | Pantalla de Digitación sin lotería, atajos de valor, registro por POST, errores, CSRF y jugadas de hoy. | 12 |
| `test_modelos.py` | Validaciones de `Jugada`, acumulación de `TotalNumero`, `Promotor`, roles de `Usuario` y admin. | 13 |
| `test_promotores.py` | Alta, edición y validaciones del catálogo, activar y desactivar, rechazo de inactivos en digitación, listado, permisos y admin sin Promotores. | 24 |
| `test_servicios.py` | `RegistroJugadaService`: fecha y hora de Caracas, acumulación, errores, transacción, token repetido y concurrencia de 8 hilos. | 11 |
| `test_totales.py` | Consolidado: orden, total, aislamiento por fecha, suma entre promotores, textos y rendimiento. | 7 |
| **Total** | | **153** |

## 6. Rendimiento medido

Medición del 09/11/2026 con `generar_datos_prueba --modo sabado` (2.535 jugadas, $14.000.000) y 50 topes de cubierta (la mitad superados).

**Método:** `runserver` local en 127.0.0.1, cliente HTTP con sesión de Administrador, 1 solicitud de calentamiento y 20 medidas por ruta.

**Equipo:** Intel Core i5-10300H 2,50 GHz, 7,8 GB de RAM, SSD, Windows 11 Home; Python 3.13.3, Django 5.2.18, SQLite 3.49.1. No es el entorno de producción.

| Ruta | Mediana (s) | Mín. (s) | Máx. (s) | RNF02 (< 2 s) |
|---|---|---|---|---|
| `/digitacion/` | 0,010 | 0,009 | 0,013 | Cumple |
| `/totales/` | 0,026 | 0,019 | 0,038 | Cumple |
| `/totales/datos/` | 0,010 | 0,008 | 0,018 | Cumple |
| `/consulta/?fecha` | 0,029 | 0,028 | 0,035 | Cumple |
| `/consulta/` con promotor | 0,025 | 0,024 | 0,032 | Cumple |
| `/consulta/` con número | 0,021 | 0,017 | 0,028 | Cumple |
| `/cubiertas/?fecha` | 0,142 | 0,129 | 0,153 | Cumple |
| `/cubiertas/<número>/` (detalle) | 0,011 | 0,011 | 0,013 | Cumple |
| `/promotores/` | 0,009 | 0,008 | 0,013 | Cumple |

## 7. Pendientes

- Pruebas y despliegue en PostgreSQL: no se han ejecutado en ese motor.
- Prueba con dos operadores reales en equipos distintos.
- Prueba de corte real de luz.
- Navegadores antiguos (RE3): sin verificar.
- Límite de intentos de ingreso: hoy no existe.
- Cierre diario (RF10): iteración 3.
- La página de Cubiertas lista todos los números del día (unas 840 filas, 240 KB) sin paginar.
