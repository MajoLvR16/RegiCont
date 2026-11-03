# Iteración 1 – RegiCont

## 1. Alcance

Historias de usuario: **HU-01** (digitar jugada), **HU-02** (consolidado por número) y **HU-06** (acceso por rol). Requisitos: RF01, RF02, RF03, RF04, RF08 y RF11.

Consulta, Cubiertas, Promotores (pantalla propia) y Cierre diario aparecen en el menú como "Próximamente" y se construirán en las iteraciones 2 y 3. `TOPE_CUBIERTA` no se creó.

## 2. Trazabilidad

| RF | Implementación | Pruebas (`ventas/tests/`) |
|---|---|---|
| RF01 Validar promotor y datos | `ventas/services.py` (`RegistroJugadaService`), `ventas/models.py` (validadores) | `test_servicios.py`, `test_modelos.py` |
| RF02 Registrar jugada | `ventas/views/jugadas.py`, `ventas/templates/jugadas/digitacion.html`, `ventas/static/js/digitacion.js` | `test_digitacion.py`, `test_servicios.py` |
| RF03 Número de 3 o 4 cifras, valor mínimo $500 | `ventas/models.py` (`Jugada`), `digitacion.js` | `test_modelos.py`, `test_digitacion.py` |
| RF04 Acumulado exacto por número | `ventas/services.py`, `ventas/models.py` (`TotalNumero.acumular`) | `test_servicios.py` (incluye concurrencia de 8 hilos), `test_modelos.py` |
| RF08 Consolidado por número | `ventas/services.py` (`ReporteService`), `ventas/views/totales.py`, `ventas/templates/totales/consolidado.html`, `ventas/static/js/totales.js` | `test_totales.py`, `test_comandos.py` (rendimiento) |
| RF11 Acceso por rol | `ventas/views/acceso.py`, `ventas/permisos.py`, `ventas/models.py` (`Usuario`), `ventas/admin.py` | `test_acceso.py`, `test_modelos.py` |

## 3. Arquitectura

```
Usuario → Vista → Controlador → Servicio → Modelo → BD
```

- Vistas: plantillas Django y JS en `ventas/templates/` y `ventas/static/js/`.
- Controladores: `AccesoController`, `JugadaController`, `TotalController` (`ventas/views/`).
- Servicios: `RegistroJugadaService` (registrar jugada y acumular total) y `ReporteService` (consolidado), en `ventas/services.py`.
- Modelos: `Usuario`, `Loteria`, `Promotor`, `Jugada`, `TotalNumero`.

## 4. Decisiones que requieren ajustar el FP15

**a) RF04: concurrencia.** El FP15 habla de "bloqueos optimistas". Se usa `transaction.atomic` + `UniqueConstraint(fecha, numero)` + suma en la BD con `F()`, y `get_or_create` que reintenta la lectura si dos operadores crean el mismo registro a la vez. Garantiza la suma exacta con varios operadores porque: (1) la suma la hace el motor de BD sobre el valor vigente, no sobre uno leído antes; (2) la constraint impide dos filas para el mismo número y fecha; (3) la jugada y su total se confirman o se revierten juntos. Equivale al flujo alterno del FP15 (detectar el conflicto y reintentar). Se comprueba con la prueba de concurrencia de 8 hilos.

**b) RF01: código inexistente.** El FP15 dice que el sistema "solicita confirmación". Se implementa un error en rojo y no se guarda nada, para evitar registrar jugadas con promotor equivocado.

**c) `TOTAL_NUMERO`.** Tiene `id` y `UniqueConstraint(fecha, numero)` en lugar de clave primaria compuesta, por robustez con el ORM de Django y el administrador.

**d) Campo técnico nuevo `JUGADA.token_envio`** (UUID, único, opcional), que no está en el FP15. Evita duplicar jugada y total si el servidor guardó pero la respuesta se perdió y el operador reintenta. Se puede retirar del modelo si no se acepta, a costa de ese riesgo.

**e) Zona horaria `America/Caracas`** (UTC-4; San Antonio del Táchira) para calcular la fecha de la jornada.

**f) Valor máximo técnico de la jugada:** 2.147.483.647.

**g) `USUARIO`.** `nombre_usuario` = `username`, `clave_hash` = `password` y `activo` = `is_active` del `AbstractUser` de Django. RF11 en el FP15 dice "ingresa credenciales y rol", pero el rol lo asigna el sistema y no se elige al ingresar.

**h) Mapeo de permisos.** El Administrador recibe `is_staff` automáticamente; el Operador no accede al administrador. `Jugada` y `TotalNumero` son de solo lectura en el administrador para no descuadrar los totales.

**i) Administración de catálogos y usuarios.** El rol Administrador gestiona Loterías, Promotores y Usuarios en un admin de Django adaptado (en español, sin borrado: se desactivan). Las pantallas propias de loterías y usuarios irán en la Iteración 2 mediante solicitud de cambio.

## 5. Rendimiento medido

Con 2.535 jugadas por $14.000.000 en SQLite, fecha 2 de noviembre de 2026:

| Ruta | Tiempo |
|---|---|
| `/totales/datos/` | 0,084 s |
| `/totales/` | 0,066 s |
| `/digitacion/` | 0,012 s |

Requisito: menos de 2 s. Es una medición con el cliente de pruebas de Django en el equipo de desarrollo, no con navegador ni red reales.

## 6. Limitaciones conocidas

- No se ha ejecutado en PostgreSQL.
- El selector de promotor usa `datalist` nativo; la selección con flechas + Enter no se verificó (escribir el código y pulsar Enter sí).
- La recuperación local y el reintento se comprobaron en navegador con respuesta perdida simulada, no con un corte real de luz.
- No hay límite de intentos de inicio de sesión.

## 7. Guía de pruebas de aceptación (FP15, sección 4.1)

Los casos suponen los datos iniciales cargados (promotores 502, 505 y 001; loterías Bogotá, Medellín y Boyacá activas) y un día sin jugadas.

### HU-01: Digitar jugada

| Caso | Datos de entrada | Criterio de aceptación | Resultado esperado | Resultado obtenido | Firma |
|---|---|---|---|---|---|
| 1.1 | Promotor 502, Bogotá, número 0742, valor 1000 | Jugada válida se guarda | Aparece en jugadas de hoy con número 0742 (conserva el cero) | | |
| 1.2 | Promotor 999, Bogotá, número 742, valor 1000 | Código de promotor inexistente | Error en rojo "Código de promotor no existe"; no se guarda | | |
| 1.3 | Promotor 502, Bogotá, número 12, valor 1000 | Número de 3 o 4 cifras | Error "El número debe tener 3 o 4 cifras"; no se guarda | | |
| 1.4 | Promotor 502, Bogotá, número 742, valor 400 | Valor mínimo $500 | Error "El valor mínimo es $500"; no se guarda | | |
| 1.5 | Promotor 502, sin elegir lotería, número 742, valor 1000 | Lotería activa obligatoria | Error "Seleccione una lotería activa"; no se guarda | | |

### HU-02: Consolidado por número

| Caso | Datos de entrada | Criterio de aceptación | Resultado esperado | Resultado obtenido | Firma |
|---|---|---|---|---|---|
| 2.1 | Sin jugadas del día; abrir Totales | Pantalla vacía | Mensaje de que no hay jugadas; total $0 | | |
| 2.2 | Digitar 742 por 1000 (promotor 502) y 742 por 2000 (promotor 505) | Suma por número | 742 aparece con $3.000 | | |
| 2.3 | Digitar 0742 por 500 y 742 por 500 | 742 y 0742 son números distintos | Dos filas separadas, $500 cada una | | |
| 2.4 | Totales: 742 con $3.000, 0742 con $500, 915 con $1.000 | Orden por monto descendente | Orden 742, 915, 0742; total general $4.500 | | |
| 2.5 | Dos operadores digitan 742 por 1000 al mismo tiempo, 5 veces cada uno | Suma exacta con concurrencia | 742 muestra $10.000 | | |

### HU-06: Acceso por rol

| Caso | Datos de entrada | Criterio de aceptación | Resultado esperado | Resultado obtenido | Firma |
|---|---|---|---|---|---|
| 6.1 | Usuario `doctor` con su contraseña | Administrador entra | Accede a Digitación; el menú muestra Administración | | |
| 6.2 | Usuario `arturo` con su contraseña | Operador entra | Accede a Digitación y Totales; sin Administración | | |
| 6.3 | `arturo` abre `/admin/` | Operador sin acceso al administrador | Es redirigido; no ve el administrador | | |
| 6.4 | Usuario `arturo` con contraseña incorrecta | Credenciales erróneas | Mensaje de error; no inicia sesión | | |
| 6.5 | Sin iniciar sesión, abrir `/totales/` | Pantallas protegidas | Redirige a inicio de sesión | | |
