# Iteración 1 – RegiCont

## 1. Alcance

| Historia de usuario | Requerimientos |
|---|---|
| HU-01 Captura y Digitación Ágil por Promotor | RF01, RF02, RF03 |
| HU-02 Totalización Automática por Número | RF04, RF08 |
| HU-06 Autenticación y Acceso Multiusuario | RF11 |

Consulta, Cubiertas, Promotores (pantalla propia) y Cierre diario aparecen en el menú como "Próximamente" y se construirán en las iteraciones 2 y 3. `TOPE_CUBIERTA` no se creó.

## 2. Trazabilidad

| RF | Implementación | Pruebas automáticas (`ventas/tests/`) |
|---|---|---|
| RF01 Registro por código de promotor/vendedor | `ventas/services.py` (`RegistroJugadaService`), `ventas/templates/jugadas/digitacion.html`, `ventas/static/js/digitacion.js` | `test_servicios.py`, `test_digitacion.py` |
| RF02 Digitación ágil de apuestas de 3 y 4 cifras | `ventas/models.py` (validadores de `Jugada`), `ventas/views/jugadas.py`, `ventas/templates/jugadas/digitacion.html`, `ventas/static/js/digitacion.js` | `test_modelos.py`, `test_servicios.py`, `test_digitacion.py` |
| RF03 Almacenamiento independiente de la transacción | `ventas/models.py` (`Jugada`), `ventas/services.py`, `ventas/static/js/digitacion.js` (recuperación local) | `test_servicios.py`, `test_digitacion.py` |
| RF04 Acumulación automática e inmediata por coincidencia | `ventas/services.py`, `ventas/models.py` (`TotalNumero.acumular`) | `test_servicios.py` (incluye concurrencia de 8 hilos), `test_modelos.py` |
| RF08 Consolidado de ventas ordenado de mayor a menor | `ventas/services.py` (`ReporteService`), `ventas/views/totales.py`, `ventas/templates/totales/consolidado.html`, `ventas/static/js/totales.js` | `test_totales.py`, `test_comandos.py` (rendimiento) |
| RF11 Control de acceso y autenticación por roles | `ventas/views/acceso.py`, `ventas/permisos.py`, `ventas/models.py` (`Usuario`), `ventas/admin.py` | `test_acceso.py`, `test_admin.py`, `test_modelos.py` |

## 3. Arquitectura

```
Usuario → Vista → Controlador → Servicio → Modelo → BD
```

- Vistas: plantillas Django y JS en `ventas/templates/` y `ventas/static/js/`.
- Controladores: `AccesoController`, `JugadaController`, `TotalController` (`ventas/views/`).
- Servicios: `RegistroJugadaService` (registrar jugada y acumular total) y `ReporteService` (consolidado), en `ventas/services.py`.
- Modelos: `Usuario`, `Loteria`, `Promotor`, `Jugada`, `TotalNumero`.

## 4. Ajustes al diseño del FP15

**Campo `token_envio` en JUGADA.** Campo técnico nuevo (UUID, único, opcional) que no está en el FP15. Evita jugadas duplicadas al reintentar tras un corte: si el servidor guardó la jugada pero la respuesta se perdió, el reintento envía el mismo token y el sistema devuelve la jugada ya guardada, sin sumarla otra vez al total.

**RF01: error en rojo en vez de "solicita confirmación".** Ante un código inexistente, el sistema muestra "Código de promotor no existe" en rojo y no guarda, para evitar jugadas con un promotor equivocado.

**RF04: transacción atómica en vez de bloqueos optimistas.** Se usa `transaction.atomic` + `UniqueConstraint(fecha, numero)` + suma en la BD con `F()`, y `get_or_create` reintenta la lectura si dos operadores crean el mismo registro a la vez. Garantiza la suma exacta porque: (1) la suma la hace el motor de BD sobre el valor vigente, no sobre uno leído antes; (2) la restricción impide dos filas para el mismo número y fecha; (3) la jugada y su total se confirman o se revierten juntos. Equivale al flujo alterno del FP15 y se comprueba con la prueba automática de 8 hilos.

**TOTAL_NUMERO con id + restricción única.** Tiene `id` y `UniqueConstraint(fecha, numero)` en lugar de clave primaria compuesta, por robustez con el ORM de Django y su administración.

**Administración en el admin de Django adaptado.** El rol Administrador gestiona Loterías, Promotores y Usuarios en el admin de Django, en español y sin opción de borrar. Las pantallas propias de loterías y usuarios están previstas para la Iteración 2, mediante solicitud de cambio.

**Otras precisiones:**

- Zona horaria `America/Caracas` (UTC-4; San Antonio del Táchira) para calcular la fecha de la jornada.
- Valor máximo técnico de una jugada: 2.147.483.647.
- USUARIO usa el `AbstractUser` de Django: `nombre_usuario` = `username`, `clave_hash` = `password`, `activo` = `is_active`. RF11 en el FP15 dice "ingresa credenciales y rol", pero el rol lo asigna el sistema y no se elige al ingresar.
- El Administrador recibe `is_staff` automáticamente; el Operador no accede a la administración. `Jugada` y `TotalNumero` son de solo lectura en el admin para no descuadrar los totales.

## 5. Rendimiento medido

Con 2.535 jugadas por $14.000.000 en SQLite, fecha 2 de noviembre de 2026:

| Ruta | Tiempo |
|---|---|
| `/totales/datos/` | 0,084 s |
| `/totales/` | 0,066 s |
| `/digitacion/` | 0,012 s |

Requisito: menos de 2 s. Es una medición con el cliente de pruebas de Django en el equipo de desarrollo, no con navegador ni red reales.

## 6. Pendientes

Para una próxima iteración o para la entrega con la cliente:

- Pruebas en PostgreSQL: no se ha ejecutado en ese motor.
- Prueba de corte real de luz: la recuperación local y el reintento se comprobaron en navegador con una respuesta perdida simulada.
- Prueba con dos operadores reales al mismo tiempo (caso 2.5 de la sección 8).
- Límite de intentos de ingreso: hoy no existe.

También queda sin verificar la selección del promotor con flechas + Enter en la lista nativa; escribir el código y pulsar Enter sí se verificó.

## 7. Usuarios por rol

Para la sección 5 del FP15.

| Usuario | Rol | Funciones |
|---|---|---|
| `doctor` | Administrador | Digitación, Totales y Administración (loterías, promotores y usuarios) |
| `arturo` | Operador | Digitación y Totales; sin acceso a la administración |
| `custodia` | Operador | Digitación y Totales; sin acceso a la administración |

**URL local de acceso:** http://127.0.0.1:8000/

**URL local de la administración:** http://127.0.0.1:8000/admin/

**Contraseñas:** Se generan con `cargar_datos_iniciales` y se entregan aparte.

## 8. Pruebas de aceptación por RF

Formato de la sección 4.1 del FP15. Los campos en blanco los llena la cliente al ejecutar las pruebas.

**Datos previos:** `cargar_datos_iniciales` ejecutado y un día sin jugadas.

**Orden de ejecución:** los totales esperados dependen del orden. Ejecute el caso 2.1 (RF08), luego 2.2 y 2.3 (RF04), luego 2.4 (RF08), y después el resto.

### RF01 Registro por código de promotor/vendedor

| Campo | Contenido |
|---|---|
| **Nombre** | Registro por código de promotor/vendedor |
| **Contexto** | El operador digita un lote de jugadas asociadas a un código de promotor. |
| **Descripción de la prueba** | El sistema debe aceptar los códigos del catálogo, rechazar los inexistentes y mantener el promotor entre jugadas. |
| **Ejecutado por** | |
| **Verificado por** | |
| **Fecha inicio / Fecha finalización** | / |
| **Datos de entrada** | **Caso 1.2:** promotor 999, Bogotá, número 742, valor 1000.<br>**Caso 1.6:** promotor 502, Bogotá, número 1721, valor 5000.<br>**Caso 1.7:** promotor 001, Bogotá, número 1722, valor 1000. |
| **Criterios de aceptación** | Permitir la entrada por teclado del código de promotor (502, 505, 512, 516, 093, 095, 001).<br>Guardar cada boleto como transacción independiente con hora, fecha y promotor. |
| **Resultado esperado** | **1.2:** error en rojo "Código de promotor no existe"; no se guarda.<br>**1.6:** se guarda con promotor 502; tras guardar siguen el promotor y la lotería, y el cursor vuelve a Número.<br>**1.7:** la tabla muestra el promotor como 001-Oficina. |
| **Resultado obtenido** | |
| **Observaciones** | |

### RF02 Digitación ágil de apuestas de 3 y 4 cifras

| Campo | Contenido |
|---|---|
| **Nombre** | Digitación ágil de apuestas de 3 y 4 cifras |
| **Contexto** | El operador captura jugadas usando solo el teclado. |
| **Descripción de la prueba** | El sistema debe validar número, valor y lotería, avanzar de campo con Enter y guardar sin recargar la página. |
| **Ejecutado por** | |
| **Verificado por** | |
| **Fecha inicio / Fecha finalización** | / |
| **Datos de entrada** | **Caso 1.1:** solo con teclado y Enter: promotor 502, Bogotá, número 0743, valor 1000.<br>**Caso 1.3:** promotor 502, Bogotá, número 12, valor 1000.<br>**Caso 1.4:** promotor 502, Bogotá, número 744, valor 400.<br>**Caso 1.5:** con la pantalla de Digitación abierta y Boyacá elegida, el Administrador desactiva Boyacá en la administración. Sin recargar, digite número 745 y valor 1000, y pulse Enter. Luego recargue la pantalla.<br>**Caso 1.8:** promotor 502, Bogotá, número 746, botón rápido $5.000 y Enter. |
| **Criterios de aceptación** | Capturar números de 3 o 4 cifras con importes a partir de $500 COP.<br>Seleccionar la lotería a la que se asocia cada jugada. |
| **Resultado esperado** | **1.1:** muestra "Registro actualizado" sin recargar la página, y la tabla muestra 0743 (conserva el cero).<br>**1.3:** error "El número debe tener 3 o 4 cifras"; no se guarda.<br>**1.4:** error "El valor mínimo es $500"; no se guarda.<br>**1.5:** al pulsar Enter, error "Seleccione una lotería activa" y no se guarda; al recargar, Boyacá ya no aparece en el selector. Vuelva a activarla al terminar.<br>**1.8:** se guarda con valor $5.000. |
| **Resultado obtenido** | |
| **Observaciones** | |

### RF03 Almacenamiento independiente de la transacción

| Campo | Contenido |
|---|---|
| **Nombre** | Almacenamiento independiente de la transacción |
| **Contexto** | Cada boleto debe quedar como un registro propio, aunque falle la conexión al guardarlo. |
| **Descripción de la prueba** | El sistema debe guardar cada jugada por separado y recuperar la que no pudo confirmar, sin duplicarla al reintentar. |
| **Ejecutado por** | |
| **Verificado por** | |
| **Fecha inicio / Fecha finalización** | / |
| **Datos de entrada** | **Caso 3.1:** dos jugadas iguales: promotor 505, Medellín, número 3331, valor 1000.<br>**Caso 3.2:** detenga el servidor, digite promotor 505, Medellín, número 3332, valor 1000, y pulse Enter. Inicie de nuevo el servidor y pulse Reintentar. |
| **Criterios de aceptación** | Guardar cada boleto como transacción independiente con hora, fecha y promotor. |
| **Resultado esperado** | **3.1:** la tabla muestra dos filas con su propia hora, número, lotería, valor y promotor.<br>**3.2:** aviso "No se pudo guardar la jugada. Revise la conexión y reintente; los datos siguen en pantalla."; al reintentar, la jugada aparece una sola vez. |
| **Resultado obtenido** | |
| **Observaciones** | El corte real de luz sigue pendiente (sección 6). |

### RF04 Acumulación automática e inmediata por coincidencia

| Campo | Contenido |
|---|---|
| **Nombre** | Acumulación automática e inmediata por coincidencia |
| **Contexto** | Varias jugadas del mismo número, de distintos promotores u operadores, deben sumarse en un solo total. |
| **Descripción de la prueba** | El sistema debe acumular en Totales cada jugada coincidente, sin importar quién la ingresó. |
| **Ejecutado por** | |
| **Verificado por** | |
| **Fecha inicio / Fecha finalización** | / |
| **Datos de entrada** | **Caso 2.2:** número 742 por 1000 (promotor 502) y número 742 por 2000 (promotor 505).<br>**Caso 2.3:** número 0742 por 500.<br>**Caso 2.5 (pendiente de ejecutar con la cliente):** `arturo` y `custodia`, en dos equipos y al mismo tiempo, digitan cada uno 5 jugadas del número 5555 por 1000. |
| **Criterios de aceptación** | Al digitar un número coincidente, el sistema debe actualizar la tabla de totales consolidados inmediatamente.<br>Mostrar la suma acumulada global por número sin importar qué promotor ingresó la apuesta. |
| **Resultado esperado** | **2.2:** una sola fila 742 con $3.000.<br>**2.3:** 0742 aparece en fila aparte con $500 y 742 sigue en $3.000.<br>**2.5:** 5555 muestra exactamente $10.000. |
| **Resultado obtenido** | |
| **Observaciones** | El caso 2.5 no se ha ejecutado con dos operadores reales; la suma concurrente solo se ha comprobado con la prueba automática de 8 hilos. |

### RF08 Consolidado de ventas ordenado de mayor a menor

| Campo | Contenido |
|---|---|
| **Nombre** | Consolidado de ventas ordenado de mayor a menor |
| **Contexto** | El operador o el Administrador consulta el recaudo de la jornada. |
| **Descripción de la prueba** | El sistema debe listar los números de mayor a menor monto, con el total del día. |
| **Ejecutado por** | |
| **Verificado por** | |
| **Fecha inicio / Fecha finalización** | / |
| **Datos de entrada** | **Caso 2.1:** sin jugadas del día, abrir Totales.<br>**Caso 2.4:** después de 2.2 y 2.3, digitar número 915 por 1000 y abrir Totales. |
| **Criterios de aceptación** | Al digitar un número coincidente, el sistema debe actualizar la tabla de totales consolidados inmediatamente.<br>Mostrar la suma acumulada global por número sin importar qué promotor ingresó la apuesta. |
| **Resultado esperado** | **2.1:** mensaje "Sin datos para ordenar" y total $0.<br>**2.4:** orden 742 ($3.000), 915 ($1.000), 0742 ($500); pie "Total de la jornada · 3 números" y total $4.500. Con Totales abierto en otro equipo, el cambio aparece sin recargar en menos de 10 s. |
| **Resultado obtenido** | |
| **Observaciones** | |

### RF11 Control de acceso y autenticación por roles

| Campo | Contenido |
|---|---|
| **Nombre** | Control de acceso y autenticación por roles |
| **Contexto** | Cada usuario ingresa con su usuario y contraseña y ve solo las funciones de su rol. |
| **Descripción de la prueba** | El sistema debe autenticar a cada usuario, restringir las funciones por rol y permitir el trabajo simultáneo. |
| **Ejecutado por** | |
| **Verificado por** | |
| **Fecha inicio / Fecha finalización** | / |
| **Datos de entrada** | **Caso 6.1:** usuario `doctor` con su contraseña.<br>**Caso 6.2:** usuario `arturo` con su contraseña.<br>**Caso 6.3:** con la sesión de `arturo`, abrir `/admin/`.<br>**Caso 6.4:** usuario `arturo` con contraseña incorrecta.<br>**Caso 6.5:** sin iniciar sesión, abrir `/totales/`.<br>**Caso 6.6:** `arturo` y `custodia` con sesión abierta en dos equipos, abriendo Totales. |
| **Criterios de aceptación** | Autenticar a cada usuario con usuario y contraseña.<br>Habilitar únicamente las funciones correspondientes al rol asignado.<br>Permitir el acceso concurrente de varios usuarios a la misma información. |
| **Resultado esperado** | **6.1:** entra a Digitación; el menú muestra Administración.<br>**6.2:** entra a Digitación y Totales; el menú no muestra Administración.<br>**6.3:** se le envía al ingreso de la administración; no ve loterías, promotores ni usuarios.<br>**6.4:** mensaje "Usuario o contraseña incorrectos"; no inicia sesión.<br>**6.5:** redirige al inicio de sesión.<br>**6.6:** ambos ven la misma información al mismo tiempo. |
| **Resultado obtenido** | |
| **Observaciones** | |
