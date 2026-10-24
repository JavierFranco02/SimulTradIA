# SimulTradIA: contexto del proyecto

Instrucciones permanentes para Claude. El **código está en los archivos del proyecto** y es la fuente de verdad;
este documento explica qué es el proyecto, cómo está organizado y cómo trabajar en él.
**La base de datos real NO está en el repo:** `database/schema.sql` es solo una guía (ver sección 7).

---

## 1. Qué es el proyecto

**SimulTradIA** es una aplicación de **escritorio** (Python + tkinter/ttkbootstrap + PostgreSQL) que funciona
como **simulador de trading e inversión con IA**.

- **Simulador:** sin dinero real. El usuario opera con un capital virtual, pero los **precios son reales**
  (descargados de APIs de mercado).
- **IA:** predice la **dirección** de un activo (alcista, bajista o lateral) con **probabilidad** y horizonte.
  **No** predice el precio exacto. El historial de aciertos es visible. La app muestra siempre que **no es
  asesoría financiera**.
- **Público y objetivo:** traders e inversores principiantes; es también un proyecto de aprendizaje.
- **Plazo y tamaño:** 2 meses, con ayuda de IA, dificultad media-alta. Alcance acotado y **mantenible**: nada
  de complejidad innecesaria.
- **Sin funciones sociales** (ranking, compartir, ligas): descartadas.
- Hay **cuenta de administrador** para gestionar el sistema.

### Alcance funcional
**Usuario:** cuenta y cuenta simulada con capital inicial (reiniciable) · mercado (buscar activos, ficha,
rankings, noticias, glosario con tooltips) · gráficos de velas con indicadores (SMA, EMA, RSI, MACD, Bollinger,
volumen) · watchlist · operar (órdenes a mercado, límite, stop-loss, take-profit; pendientes e historial) ·
portafolio y métricas (rentabilidad, drawdown, % de aciertos) · **backtesting** con constructor visual de
reglas y comparación contra comprar y mantener · **IA** (predicción de dirección, explicación de factores,
historial de aciertos, sentimiento de noticias, escáner de oportunidades) · **replay histórico** (operar en una
fecha pasada mientras las velas avanzan) · **coach de IA** (analiza las operaciones cerradas y detecta patrones).

**Administrador:** usuarios (listar, desactivar/reactivar, reiniciar cuenta, rol) · activos (agregar por ticker,
desactivar) · ingesta de datos (estado, errores, ejecución manual) · modelos de IA (métricas, precisión real,
reentrenar, activar o revertir versión) · glosario · panel de resumen · auditoría. El admin nunca ve
contraseñas ni opera dentro de la cuenta de un usuario; sus permisos se validan en los servicios, no solo
ocultando botones; el primer admin se crea por script (`scripts/crear_admin.py`), nunca desde el registro público.

**Opcional si sobra tiempo:** alertas, varias cuentas simuladas, predicción de volatilidad.
**Descartado:** social, tutoriales y retos, chat asistente, datos fundamentales, calendario, posiciones cortas,
guardar configuraciones de gráfico, exportar PDF/CSV.

### Enfoque de la IA
- Predicción de **dirección con probabilidades** (`prob_alcista + prob_bajista + prob_lateral = 1`) y confianza.
  Se guarda el `precio_referencia` y la `fecha_objetivo`; al vencer, un proceso completa `direccion_real` y
  `acierto`, y de ahí sale el historial.
- Empezar con **LightGBM** sobre indicadores, validar con **walk-forward** (entrenar con el pasado, probar con
  el futuro, en orden cronológico) y comparar contra una línea base. Explicaciones con SHAP.
- Sentimiento de noticias con un modelo de lenguaje. El coach usa estadísticas simples y un modelo de lenguaje
  que redacta el informe.
- Ser honesto: un modelo que "acierta siempre" suele tener sobreajuste o filtrar datos del futuro.

---

## 2. Cómo trabajar en este proyecto

1. **Responde en español** y explica en **lenguaje simple**. El usuario no conoce el mundo del trading y a veces
   se pierde con patrones de arquitectura (por ejemplo, callbacks): usa analogías y recorridos paso a paso.
   Cuando propongas archivos o carpetas, explica **para qué sirve cada pieza**.
2. **Recomienda con argumentos y deja que él decida.** Él cuestiona los diseños y razona sus decisiones. No
   reabras decisiones tomadas (sección 6) salvo que detectes un problema real; si es así, dilo con el motivo.
3. **Entrega los cambios como archivos modificados:** Realiza los cambios pertinentes, luego di qué archivos se modificaron o carpetas. Entrega el `.zip`completo. Mantén tu copia interna del proyecto actualizada.
4. **Lee el archivo actual antes de modificarlo o sobrescribirlo.** Puede haber cambiado desde la última vez
   que lo viste. Si no tienes el código a mano, pídelo antes de escribir cambios.
5. **Respeta la arquitectura y su estructura de carpetas** (secciones 4 y 5). Si algo no encaja, propón
   el ajuste en lugar de saltarte la capa.
6. **No compliques.** Nada de archivos o abstracciones sin uso real, ni ajustes, reglas o estilos para
   valores que se usan en un solo lugar.
7. **El esquema SQL es una guía, no la base real.** Antes de escribir SQL o entidades que toquen una tabla, confirma
   con el usuario qué columnas tiene realmente; no asumas lo que dice `schema.sql`.
8. **Verifica y sé honesto con lo verificado.** Ejecuta las pruebas (sección 8). Tu entorno normalmente no
   tiene tkinter, ttkbootstrap, psycopg2 ni PostgreSQL: lo que simules valida lógica y cableado, **no la
   apariencia real ni la conexión real**. Dilo siempre que aplique.

---

## 3. Stack y entorno

| Pieza | Elección | Nota |
|---|---|---|
| Lenguaje | Python 3.8 o superior | Usa `Optional`/`Dict` de `typing`, no `X \| None`. |
| Interfaz | `tkinter` + **`ttkbootstrap`** | Tema actual: `darkly`. |
| Base de datos | **PostgreSQL 9.3** | Sin JSONB, IDENTITY, `FILTER`, `EXECUTE FUNCTION`, `ON CONFLICT` ni TimescaleDB. |
| Conector | **`psycopg2-binary`** | `psycopg` v3 es para PostgreSQL 10 o superior. Cursores `NamedTupleCursor` (filas por nombre). |
| Contraseñas | **`argon2-cffi`** | Nunca se guarda la contraseña real. |
| Configuración | `python-dotenv` | Datos de conexión en `.env` (no se sube a Git): `BD_HOST`, `BD_PUERTO`, `BD_NOMBRE`, `BD_USUARIO`, `BD_PASSWORD`. |
| Instalación | `pyproject.toml` (layout `src`) | `pip install -e .` una vez; las dependencias viven en `pyproject.toml`. Sin `sys.path.insert`. |
| Pruebas | `unittest` | Sin dependencias extra. |

Previstas para módulos futuros (se suman a `pyproject.toml` cuando se usen): `yfinance` o `ccxt` (precios),
`matplotlib` + `mplfinance` (velas con `FigureCanvasTkAgg`), `pandas` y `pandas-ta`, `scikit-learn`, `lightgbm`,
`shap`, `APScheduler`. Los gráficos de tkinter sirven para velas diarias y backtests, no para tiempo real fluido.

---

## 4. Arquitectura

### 4.1 Capas y quién conoce a quién
Analogía del restaurante: la **vista** es la mesa, el **controlador** el mesero, el **servicio** el cocinero, el
**repositorio** la despensa y el **Navegador** el encargado de sala. La mesa no cocina y el cocinero no sabe que
existen las mesas.

```
Vista ──callbacks (vincular_acciones)──► Controlador ──► Servicio ──► Repositorio ──► PostgreSQL
                                                          Dominio (entidades, enums, reglas)   Núcleo (core)
```

| Capa | Hace | No hace |
|---|---|---|
| **Vista** (`iu/<módulo>/*_view.py`) | Dibuja widgets; expone métodos para leer y mostrar datos. Pasiva. | Lógica, SQL, llamar a servicios. |
| **Controlador** (`iu/<módulo>/*_controller.py`) | Intermediario: lee la vista, lanza el trabajo en segundo plano, decide qué hacer con el resultado (navegar con `navegador.ir_a`, mostrar error, abrir/cerrar sesión). | Importar vistas (recibe la vista ya creada). |
| **Servicio** (`services`) | Reglas de negocio y **validaciones**. Abre la transacción y llama a **repositorios** (combina repositorios, no llama transacciones de otros servicios). Los métodos de administración (cuando existan) reciben el `actor` y llaman a `exigir_admin`. | Conocer tkinter o escribir SQL. |
| **Repositorio** (`repositories`) | **Único lugar con SQL.** Convierte filas en entidades leyendo por **nombre de columna**. | Reglas de negocio. Concatenar SQL con datos: siempre parámetros `%s`. |
| **Dominio** (`domain`) | Entidades (`dataclass`), enums y `reglas/` (reglas puras reutilizadas: comisión, precio promedio...). Python puro. | Depender de nada. |
| **Núcleo** (`core`) | Herramientas técnicas reutilizables: ajustes, conexión, seguridad, sesión, excepciones, logging. Puede usar `domain`. | Conocer el negocio; importar `services`, `repositories` o `iu`; usar tkinter. |
| **Composición** (`composition.py`, `main.py`) | `crear_servicios(db)` arma servicios + repositorios en UN lugar (lo usan `main.py`, `worker.py` y `scripts/`). `main.py` crea la BD y la entrega a `App`. | |
| **App y Navegador** (`app.py`, `iu/navegacion.py`) | `App` es la ventana: crea `Session` y `Navegador`. El Navegador cambia de pantalla por nombre. | |

### 4.2 Carpetas
```
main.py              arranque de la app con ventanas (crea BD y servicios)
worker.py            (PREVISTO, aún no existe) proceso SIN ventanas para tareas programadas; solo programa los jobs
scripts/             programas que se ejecutan a mano (p. ej. crear_admin.py)
database/schema.sql  esquema de GUÍA (no es la base real; ver sección 7)
pyproject.toml       paquete instalable (pip install -e .) y dependencias
tests/               fakes.py compartido; subcarpetas core/, services/, iu/
src/simultradia/
  app.py             ventana principal
  composition.py     Servicios + crear_servicios(db)
  core/              settings, db, security, session, exceptions, logging_config
  domain/            enums.py, entities/ (*_entity.py), reglas/ (previsto: reglas puras compartidas)
  repositories/      *_repository.py
  services/          *_service.py, permisos.py
  clients/           (previsto) adaptadores a APIs externas (yfinance, ccxt, Finnhub, LLM): solo traen datos
  analisis/          (previsto) cálculos puros sobre series (SMA, RSI, drawdown, Sharpe...)
  backtesting/       (previsto) motor de simulación puro (sin BD ni UI)
  jobs/              (previsto) tareas del worker (ingesta, evaluar predicciones, órdenes pendientes)
  ia/                (previsto) modelos y lógica de IA (subdividir en features/entrenamiento/prediccion/explicacion al crecer)
  iu/                interfaz de usuario, agrupada por funcionalidad
    styles.py        Fonts, Colors, ButtonStyle, Spacing
    background.py    ejecutar_en_hilo / iniciar_revision (hilos de la interfaz)
    navegacion.py    Navegador: ir_a("nombre", **parametros)
    rutas.py         registra las pantallas de todos los módulos
    components/      clases reutilizables (FormField, PasswordField, StatusMessage, ActionButton...)
    base/            FormView y FormController (base de los formularios)
    auth/            login y registro (vistas, controladores, pantallas.py)
    shell/           ventana "home": menú lateral + área de contenido (ShellView, ShellController)
    inicio/          sección de bienvenida del panel
    <módulo>/        mercado/, trading/, backtesting/, ia/, admin/... cuando lleguen
```
**(previsto)** = la carpeta existe solo con su `__init__.py` y un docstring; se llena cuando llegue su módulo.
Cada módulo de `iu/` tiene su `pantallas.py` con `registrar(navegador)`; `iu/rutas.py` los junta.
El paquete se llama **`simultradia`** (no `main`: chocaría con `main.py`).

### 4.3 Piezas que conviene entender
- **Callbacks:** la vista tiene un "enchufe" vacío (`vincular_acciones(al_algo=...)`) que el controlador conecta
  pasando **su método sin paréntesis**. La vista no depende de ningún controlador concreto. El mismo patrón
  se usa en `ejecutar_en_hilo(trabajo, al_terminar=..., al_fallar=...)`.
- **Hilos:** tkinter solo deja tocar widgets desde el hilo principal. El trabajo lento corre en un hilo; su
  resultado vuelve por una cola que `iniciar_revision(root)` (en `iu/background.py`) vacía cada 100 ms. En
  `FormController._ejecutar`, tanto el **éxito como el error** se descartan si `vista.esta_viva()` es falso.
- **Navegador y shell:** `Navegador.ir_a(nombre, **parametros)` (lo reciben los controladores). Hay pantallas
  **a ventana completa** (login, registro, home) y **secciones** (`en_shell=True`) que se dibujan dentro del área
  de contenido del shell (`home`), con el menú lateral fijo. Cada pantalla se registra con una **fábrica**
  `(padre, navegador, **parametros) -> vista` que arma vista + controlador y usa `navegador.servicios` y
  `navegador.session`. El tamaño de la ventana lo declara cada ruta (`tamano`, `minimo`). Una vista de shell
  expone `contenido` y `marcar_seccion(nombre)`. El menú está en `iu/shell/pantallas.py` (`_MENU`, con marca de solo admin).
- **Sesión:** `Session` (en `core`) guarda el usuario actual. **La crea `App` (una sola) y se inyecta** al Navegador
  y a los controladores que la necesitan; no hay singleton global. El servicio **solo autentica y devuelve el usuario**
  (`autenticar`); el **controlador abre la sesión** cuando el resultado llega a una pantalla vigente.
- **Errores:** todos los esperados heredan de `ErrorAplicacion` (su mensaje se puede mostrar tal cual).
  `DatosInvalidos` lleva `{campo: mensaje}` y el controlador base lo reparte **bajo cada campo** de la vista.
  Los errores que no son de un campo (credenciales, cuenta desactivada, permisos, conexión) van al **mensaje general**.
  Cualquier otra excepción es inesperada: se registra en el log y el usuario ve un mensaje genérico.
  Las claves de campo (`"nombre"`, `"email"`, `"password"`, `"confirmacion"`) son compartidas entre servicio y vista;
  `FormView.valores()` devuelve `{clave: texto}` para que el controlador lea el formulario.
- **Permisos:** los métodos de administración (cuando existan) reciben `actor: Usuario` (el controlador pasa `session.usuario`) y
  llaman a `exigir_admin(actor)` (`services/permisos.py`), que lanza `ErrorPermisos`.
- **Transacciones:** `with db.obtener_conexion() as conn:` presta una conexión; commit al salir bien, rollback
  si falla, y siempre la devuelve al pool. Todo lo hecho dentro es una sola operación (p. ej. el registro crea
  el usuario y su cuenta simulada juntos).
- **Estilos y componentes:** todo componente es una **clase**. Fuentes, colores y espacios salen solo de
  `iu/styles.py` (`Fonts` por rol con la familia en `Fonts.FAMILY`; fuentes con nombre de Tk). Nunca se escriben a mano.
- **Errores bajo cada campo:** `FormField` incluye un `StatusMessage` oculto que **no ocupa espacio** hasta tener
  texto (tira invisible de 1 px porque Tk no recalcula el tamaño de un contenedor vacío), usa **todo el ancho
  disponible** (el `wraplength` sigue al ancho del mensaje) y se oculta cuando el texto del campo cambia
  (`StringVar.trace_add`, no `<KeyRelease>`).

### 4.4 Para agregar una pantalla
**Formulario:**
1. Vista que hereda de `FormView`: `_agregar_campo(clave, campo)`, `_agregar_mensaje()`,
   `_agregar_boton_principal(...)` y un `vincular_acciones(...)`.
2. Controlador que hereda de `FormController`: conecta las acciones y llama a `self._ejecutar(trabajo, al_terminar=...)`.
3. Servicio con la lógica y las validaciones; repositorio con el SQL; entidad si hay un concepto nuevo; y las tablas o columnas nuevas en la base real (se toma `schema.sql` como guía y se ajusta).
4. En el `pantallas.py` del módulo, una fábrica y su `registrar` (`navegador.registrar("nombre", fabrica, ...)`).

**Sección del panel** (mercado, portafolio...): carpeta `iu/<módulo>/` con vista (`ttk.Frame` + `vincular_acciones`),
controlador simple si hace falta y `pantallas.py` registrando con `en_shell=True`; sumar el módulo en `iu/rutas.py`
y su botón en `_MENU` de `iu/shell/pantallas.py`. Se navega con `navegador.ir_a("nombre", ...)`.

---

## 5. Convenciones

**Nombres.** Carpetas, archivos y clases **estructurales en inglés** (`usuario_entity.py`, `UsuarioService`,
`LoginController`, `Database`, `Session`, `Navegador`). Nombres **de negocio, métodos, parámetros y variables en español**
(`iniciar_sesion`, `buscar_por_email`, `obtener_conexion`, `mostrar_error`, `establecer_ocupado`). Archivos en
`snake_case` con sufijo de capa (`_entity`, `_repository`, `_service`, `_view`, `_controller`); clases en
`PascalCase`; constantes en `MAYUSCULAS`; privados con `_`; callbacks con prefijo `al_`. Un nombre debe decir
lo que hace: `autenticar` verifica y no inicia sesión; el controlador es quien la inicia.
**Base de datos:** clave primaria `id_<entidad>` y las foráneas con el mismo nombre (`usuarios.id_usuario`,
`cuentas_simuladas.id_usuario`).

**Código.**
- Dinero con `Decimal`, nunca `float`. SQL siempre con parámetros. Filas leídas por nombre, nunca por posición.
- Compatible con Python 3.8. Comentarios y docstrings en español, explicando el porqué.
- Cada carpeta de código tiene su `__init__.py`.
- **Un valor que se usa en un solo lugar va en línea, donde se usa.** Solo suben a `settings.py` los valores que
  cambian por entorno (base de datos) o se usan en varios sitios, y a `styles.py` los tokens usados 2 o más veces.

**Dónde va cada cosa.**
| Si es... | Va en... |
|---|---|
| Dibujar un widget o leer lo escrito | Vista |
| Reaccionar a un evento y decidir (llamar, mostrar error, navegar, abrir/cerrar sesión) | Controlador |
| Regla de negocio o **validación** | Servicio, en funciones pequeñas por campo |
| SQL | Repositorio |
| Concepto del negocio / lista cerrada de valores | `domain/entities` / `domain/enums.py` |
| Cálculo de negocio puro usado en varios módulos | `domain/reglas` |
| Cálculo numérico sobre series de precios | `analisis/` |
| Llamada a una API externa | `clients/` |
| Tarea programada del worker | `jobs/` |
| Algo técnico reutilizable | `core/` |
| Fuente, color o espaciado compartido | `iu/styles.py` |

---

## 6. Decisiones de diseño (no reabrir sin motivo)

1. **Controladores como intermediarios** y vistas pasivas; el servicio no sabe que existen pantallas. Permite probar los controladores sin ventanas.
2. **Validaciones en el servicio, por campo y reutilizables** (`_error_nombre`, `_error_email`, `_error_password`, `_error_confirmacion`), combinadas por caso de uso; `_lanzar_si_hay_errores` avisa de **todos** los problemas a la vez. **Sin archivo externo de reglas.** No se mueven a un módulo compartido hasta que un segundo servicio las necesite.
3. **El login valida el formato del email pero no el largo de la contraseña:** esa regla es para elegir una, no para entrar. La confirmación de contraseña también se valida en el servicio.
4. **Seguridad del login:** si el email no existe se hace una verificación de relleno (`gastar_tiempo_de_verificacion`); la **cuenta desactivada se avisa después** de comprobar la contraseña.
5. **Sesión inyectada, no global;** servicio sin efectos secundarios; el controlador abre la sesión solo si la pantalla sigue vigente.
6. **Ajustes mínimos:** `settings.py` solo tiene `app` y `database`. Tema (`app.py`), tamaño de ventana (cada `pantallas.py`), pool de conexiones y reglas de longitud están en línea donde se usan.
7. **Fuentes y demás estilos en `styles.py`;** una sola línea (`Fonts.FAMILY`) cambia la fuente de toda la app.
8. **Clases base `FormView` y `FormController`** (en `iu/base/`) para lo que se repetía entre formularios; los componentes son clases. El título y subtítulo del formulario los dibuja `FormView`.
9. **Errores de campo bajo su campo,** ocultos sin ocupar espacio, a todo el ancho y que desaparecen al escribir.
10. **`psycopg2` y `BIGSERIAL`/`JSON`** por PostgreSQL 9.3; contraseñas con argon2.
11. **El registro público solo crea usuarios normales** y crea su cuenta simulada (capital inicial 10 000 USD) **en la misma transacción**. El administrador (creado por script) no tiene cuenta simulada.
12. **`worker.py` separado, previsto** (aún no existe; sin ventanas, mismos servicios y repositorios vía `composition.crear_servicios`, misma BD).
13. **Un solo mercado y pocos activos (20 a 30)** al inicio.
14. **Credenciales de BD en el cliente:** aceptado para un proyecto académico.
15. **Panel de una sola ventana (shell):** tras el login, `home` muestra menú lateral fijo y las secciones se intercambian en el área de contenido; el login usa el mismo Navegador (a ventana completa). Los controladores reciben el `Navegador`, no la `App`.
16. **`App` no arma servicios:** `main.py` crea `Database` y `crear_servicios(db)`; `App` solo recibe los servicios.
17. **`iu/` agrupado por funcionalidad;** el backend, por capas.
18. **Filas por nombre** (`NamedTupleCursor` en `Database`), nunca por índice.
19. **Claves `id_<entidad>`** en todas las tablas.
20. **El servicio de usuarios se mantiene como `UsuarioService`** (parámetro `usuario_service`); se separará en `AuthService` y `UsuarioAdminService` solo cuando entre la administración de usuarios. Pendiente de decidir: `BaseController`/`BaseView` (hoy `esta_viva` y `_ejecutar` viven en los formularios).
21. **Migraciones:** descartadas por ahora; la base real se ajusta a mano según se necesite.
22. **El esquema SQL es orientativo:** la base real hoy solo tiene `usuarios` (recortada, sin `avatar_url`) y va a sufrir modificaciones; el código y el usuario mandan sobre `schema.sql`.

---

## 7. Base de datos (PostgreSQL 9.3)

**`database/schema.sql` es una GUÍA de lo que la base podría llegar a tener, no la fuente de verdad.** La base real
empieza solo con la tabla `usuarios` (recortada: sin `avatar_url`, por ejemplo) y se irá ajustando por módulo:
tablas, columnas y nombres pueden cambiar o no existir. Lo que sí es regla: PostgreSQL 9.3, claves `id_<entidad>` y los tipos
de abajo. Lo demás es el diseño orientativo:

- **Versión 9.3:** `BIGSERIAL`, `JSON`, `COUNT(CASE WHEN ...)`, `EXECUTE PROCEDURE` en triggers, sin `ON CONFLICT` ni `CREATE INDEX IF NOT EXISTS`, sin TimescaleDB.
- **Claves:** PK `id_<entidad>` (`usuarios.id_usuario`, `activos.id_activo`, `cuentas_simuladas.id_cuenta`, `ordenes.id_orden`...); las foráneas llevan el mismo nombre. Índice único `lower(email)`: el email se guarda en minúsculas.
- **Tipos:** dinero `NUMERIC(20,4)`, precios `NUMERIC(20,8)`, cantidades `NUMERIC(28,10)`, porcentajes como número legible (5.25 = 5,25 %), **probabilidades de la IA de 0 a 1**, fechas `TIMESTAMPTZ` en UTC.
- **Ideas clave del modelo (orientativas):**
  - `ordenes` es la intención del usuario y `ejecuciones` lo que realmente ocurrió; el historial sale de `ejecuciones`.
  - `posiciones` (solo largas) es lo que posee ahora; al vender todo se borra la fila y se registra en `operaciones_cerradas`.
  - `snapshots_portafolio` es la foto diaria del patrimonio; `cotizaciones_actuales` es la caché de la última cotización.
  - `sesiones_replay` usa una cuenta propia con `es_replay = TRUE`.
  - `predicciones_direccion` guarda lo predicho y lo ocurrido (`acierto`); `vista_precision_modelos` calcula el historial.
  - `estrategias.definicion` (JSON) guarda las reglas del backtesting.
- **Fuera del esquema (descartadas):** configuraciones de gráfico, datos fundamentales, calendario de eventos, chat asistente, tutoriales y retos, y posiciones cortas. No hay enums ni columnas para ellas.
- **Compra/venta vs. larga/corta:** `ordenes.lado` (`compra`/`venta`) sí existe; `posiciones` no tiene `lado` porque solo hay posiciones largas (vender cierra o reduce la posición).
- **Vistas y función:** `vista_posiciones_valoradas`, `vista_resumen_cuenta`, `vista_estadisticas_operaciones`, `vista_precision_modelos`, `reiniciar_cuenta(id_cuenta)`.

---

## 8. Pruebas

- Desde la raíz: `python -m unittest discover -s tests -t . -v` (con `pip install -e .` hecho). No necesitan PostgreSQL ni ventanas.
- Estructura: `tests/fakes.py` (falsos compartidos) y subcarpetas `core/`, `services/`, `iu/`, cada una con `__init__.py`; se importa `from tests.fakes import ...`.
- **Servicios:** `DatabaseFalsa`, `RepositorioFalso`, `CuentaRepositorioFalso`.
- **Controladores:** `VistaFalsa`, `NavegadorFalso` (registra `(nombre, parametros)` de `ir_a`), `ServicioFalso` y una `Session()` propia por prueba; `ejecutar_en_hilo` se reemplaza con `mock.patch("simultradia.iu.base.form_controller.ejecutar_en_hilo", ...)` (en el acto, o diferido).
- **Navegador:** `VentanaFalsa`, `PantallaFalsa`, `ShellFalso`.
- **Entorno de Claude:** sin tkinter, ttkbootstrap, psycopg2, argon2 ni red. Se verifica con módulos simulados (stubs) en una carpeta temporal y `PYTHONPATH`. Lo visual y la conexión real solo los puede comprobar el usuario.

---

## 9. Qué evitar

Archivos de "reglas" o "validaciones" externos · singletons globales · SQL fuera de repositorios · lógica en
vistas · tkinter en servicios o en `core` · componentes como funciones · `float` para dinero · ajustes, estilos o
tokens para valores de un solo uso · fuentes, colores o espacios escritos a mano en vistas o componentes ·
filas leídas por posición · `sys.path.insert` · sobrescribir un archivo sin ver antes su estado actual ·
afirmar que algo funciona visualmente sin haberlo visto.
