# SimulTradIA: contexto del proyecto

Instrucciones permanentes para Claude. El **código está en los archivos del proyecto** y es la fuente de verdad;
este documento explica qué es el proyecto, cómo está organizado y cómo trabajar en él.
**La base de datos real NO se describe del todo en el repo:** `database/schema.sql` es solo una guía y
`database/mercado.sql` crea las tablas reales del módulo Mercado (ver sección 7).
El estado actual y lo que falta están en la sección 10.

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
**Usuario:** cuenta y cuenta simulada con capital inicial (reiniciable) · mercado (buscar activos, gráfico,
rankings, noticias, glosario con tooltips) · gráficos de velas con indicadores (SMA, EMA, Bollinger, RSI, MACD,
volumen) · watchlist · operar (órdenes a mercado, límite, stop-loss, take-profit; pendientes e historial) ·
portafolio y métricas (rentabilidad, drawdown, % de aciertos) · **backtesting** con constructor visual de
reglas y comparación contra comprar y mantener · **IA** (predicción de dirección, explicación de factores,
historial de aciertos, sentimiento de noticias, escáner de oportunidades) · **replay histórico** (operar en una
fecha pasada mientras las velas avanzan) · **coach de IA** (analiza las operaciones cerradas y detecta patrones).

**Administrador:** usuarios (listar, desactivar/reactivar, reiniciar cuenta, rol) · activos (agregar por ticker,
editar, desactivar, **elegir, probar y cambiar su fuente de datos**) · ingesta de datos (estado, fuentes, probar conexión,
ejecución manual de todo o de una fuente) · **contraseña temporal** para quien olvidó la suya ·
modelos de IA (métricas, precisión real, reentrenar, activar o revertir versión) · glosario · panel de resumen ·
auditoría. El admin nunca ve contraseñas ni opera dentro de la cuenta de un usuario; sus permisos se validan en los
servicios, no solo ocultando botones; el primer admin se crea por script (`scripts/crear_admin.py`), nunca desde el
registro público.

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
3. **Entrega los cambios SIEMPRE como un `.zip`** con los archivos **NUEVOS y MODIFICADOS** (mismas rutas que en el
   repo, archivos completos). **No des código para copiar y pegar** ni fragmentos por archivo: esa mecánica ya no se
   usa. Junto al zip, di solo qué archivos se **agregaron**, cuáles se **modificaron** y cuáles hay que **borrar a
   mano** (un zip no puede borrar), más lo que no pudiste verificar. Mantén tu copia interna del proyecto actualizada.
4. **Lee el archivo actual antes de modificarlo o sobrescribirlo.** Puede haber cambiado desde la última vez
   que lo viste. Si no tienes el código a mano, pídelo antes de escribir cambios.
5. **Respeta la arquitectura y su estructura de carpetas** (secciones 4 y 5). Si algo no encaja, propón
   el ajuste en lugar de saltarte la capa.
6. **No compliques.** Nada de archivos o abstracciones sin uso real, ni ajustes, reglas o estilos para
   valores que se usan en un solo lugar. **Interfaz:** el usuario no quiere tarjetas de resumen donde la
   información se pueda mostrar de otra forma (texto, filas, tablas), y prefiere interruptores visibles (no botones)
   para activar o desactivar opciones.
7. **El esquema SQL es una guía, no la base real.** Antes de escribir SQL o entidades que toquen una tabla,
   confirma con el usuario qué columnas tiene realmente; no asumas lo que dice `schema.sql`. Las tablas de Mercado
   sí están definidas en `database/mercado.sql`.
8. **Verifica y sé honesto con lo verificado.** Ejecuta las pruebas (sección 8). Tu entorno normalmente no
   tiene tkinter, ttkbootstrap, psycopg2, ccxt ni yfinance, ni red: lo que simules valida lógica y cableado, **no la
   apariencia real, ni la conexión real a PostgreSQL, Binance o Yahoo**. El dibujo del gráfico sí se puede probar
   (matplotlib sin tkinter). Dilo siempre que aplique.

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
| Precios | **`ccxt`** (Binance, cripto) y **`yfinance`** (Yahoo Finance: acciones, ETF, divisas, índices, bonos) | Sin cuentas ni claves. Yahoo llega con ~15 min de retraso en acciones, ETF e índices y limita las peticiones. |
| Gráficos | **`matplotlib`** (`FigureCanvasTkAgg`) | Sirve para velas diarias e intradía con un refresco de 2 s; no para animación fluida a muchos cuadros por segundo. |
| Instalación | `pyproject.toml` (layout `src`) | `pip install -e .` una vez; las dependencias viven en `pyproject.toml`. Sin `sys.path.insert`. |
| Pruebas | `unittest` | Sin dependencias extra (las de pandas se saltan si no está instalado). |

Previstas para módulos futuros (se suman a `pyproject.toml` cuando se usen): `pandas` y `pandas-ta` solo si hacen
falta (los indicadores actuales son Python puro), `scikit-learn`, `lightgbm`, `shap`, `APScheduler` (el worker usa
hoy un bucle simple).

---

## 4. Arquitectura

### 4.1 Capas y quién conoce a quién
Analogía del restaurante: la **vista** es la mesa, el **controlador** el mesero, el **servicio** el cocinero, el
**repositorio** la despensa, el **cliente** el proveedor que trae ingredientes de afuera y el **Navegador** el
encargado de sala. La mesa no cocina y el cocinero no sabe que existen las mesas.

```
Vista ──callbacks (vincular_acciones)──► Controlador ──► Servicio ──► Repositorio ──► PostgreSQL
                                                          │ └──────► Cliente ──► APIs externas (Binance, Yahoo)
                                                          Dominio (entidades, enums, reglas)   Núcleo (core)   Análisis (cálculo puro)
```

| Capa | Hace | No hace |
|---|---|---|
| **Vista** (`iu/<módulo>/*_view.py`) | Dibuja widgets; expone métodos para leer y mostrar datos. Pasiva. | Lógica, SQL, llamar a servicios. |
| **Controlador** (`iu/<módulo>/*_controller.py`) | Intermediario: lee la vista, lanza el trabajo en segundo plano, decide qué hacer con el resultado (navegar con `navegador.ir_a`, mostrar error, abrir/cerrar sesión, refrescar cada pocos segundos). | Importar vistas (recibe la vista ya creada). |
| **Servicio** (`services`) | Reglas de negocio y **validaciones**. Abre la transacción y llama a **repositorios** y **clientes** (combina repositorios, no llama transacciones de otros servicios). Los métodos de administración reciben el `actor` y llaman a `exigir_admin`. | Conocer tkinter o escribir SQL. Llamar a una API externa con una conexión de BD abierta. |
| **Repositorio** (`repositories`) | **Único lugar con SQL.** Convierte filas en entidades leyendo por **nombre de columna**. | Reglas de negocio. Concatenar SQL con datos: siempre parámetros `%s`. |
| **Cliente** (`clients`) | Adaptador a una API externa: **solo trae datos** y los devuelve como entidades. Declara qué tipos de activo ofrece (`TIPOS`), cómo se escriben sus tickers (`PATRON_TICKER`, `EJEMPLO_TICKER`), su `NOMBRE` (igual al de la tabla `fuentes_datos`) y su ritmo (`segundos_entre_cotizaciones`, `segundos_entre_velas`). | Escribir en la BD o decidir algo. |
| **Dominio** (`domain`) | Entidades (`dataclass`), enums y `reglas/` (reglas y parámetros puros compartidos: intervalos, indicadores...). Python puro. | Depender de nada. |
| **Análisis** (`analisis`) | Cálculo puro sobre series y velas: agrupar velas, aplicar el precio en vivo, SMA, EMA, Bollinger, RSI, MACD. | BD, red o interfaz. |
| **Núcleo** (`core`) | Herramientas técnicas reutilizables: ajustes, conexión, seguridad, sesión, excepciones, logging. Puede usar `domain`. | Conocer el negocio; importar `services`, `repositories` o `iu`; usar tkinter. |
| **Composición** (`composition.py`, `main.py`, `worker.py`) | `crear_servicios(db)` arma servicios + repositorios + clientes en UN lugar (lo usan `main.py`, `worker.py` y `scripts/`). `main.py` crea la BD y la entrega a `App`. | |
| **App y Navegador** (`app.py`, `iu/navegacion.py`) | `App` es la ventana: crea `Session` y `Navegador`. El Navegador cambia de pantalla por nombre. | |

### 4.2 Carpetas
```
main.py              arranque de la app con ventanas (crea BD y servicios)
worker.py            proceso SIN ventanas (python worker.py): precios cada 2 s, velas cada 60 s; cada fuente a su ritmo.
                     Solo programa los jobs
scripts/             programas que se ejecutan a mano (p. ej. crear_admin.py)
database/            schema.sql = GUÍA (no es la base real) · mercado.sql = tablas REALES de Mercado
                     (fuentes_datos, activos, precios_velas, cotizaciones_actuales) + 30 activos ·
                     mercado_actualizar.sql = una sola vez, para quien ya tenía la versión solo cripto (se puede borrar) ·
                     usuarios_password_temporal.sql = una sola vez: agrega usuarios.debe_cambiar_password (se puede borrar)
pyproject.toml       paquete instalable (pip install -e .) y dependencias
tests/               fakes.py compartido; subcarpetas core/, services/, iu/, analisis/, clients/
src/simultradia/
  app.py             ventana principal
  composition.py     Servicios + crear_servicios(db) (registra también los clientes por nombre de fuente)
  core/              settings, db, security, session, exceptions, logging_config
  domain/            enums.py (RolUsuario, TipoActivo, IntervaloVela)
                     entities/ (*_entity.py: usuario, cuenta_simulada, activo, fuente, cotizacion [+ ActivoCotizado,
                       PanelMercado], vela)
                     reglas/ (intervalos.py: qué se guarda y qué se deriva; indicadores.py: parámetros)
  repositories/      usuario, cuenta, activo, fuente, precio  (*_repository.py)
  services/          usuario_service (login, registro) · usuario_admin_service · mercado_service · grafico_service ·
                     ingesta_service · activo_admin_service · fuente_admin_service · permisos.py · validacion.py
  clients/           binance_client.py (ccxt), yahoo_client.py (yfinance): solo traen datos
  analisis/          velas.py (agrupar, aplicar precio), indicadores.py (SMA, EMA, Bollinger, RSI, MACD)
  backtesting/       (previsto) motor de simulación puro (sin BD ni UI)
  jobs/              actualizar_cotizaciones_job.py, actualizar_velas_job.py (el worker los repite)
  ia/                (previsto) modelos y lógica de IA (subdividir en features/entrenamiento/prediccion/explicacion al crecer)
  iu/                interfaz de usuario, agrupada por funcionalidad
    styles.py        Fonts, Colors, Palette (gráfico y tabla), ButtonStyle, Spacing
    formato.py       números, porcentajes, fechas y nombres de tipos en español (Python puro)
    background.py    ejecutar_en_hilo / iniciar_revision (hilos de la interfaz)
    navegacion.py    Navegador: ir_a("nombre", **parametros)
    rutas.py         registra las pantallas de todos los módulos
    components/      clases reutilizables: ActionButton, FormField, PasswordField, ShowPasswordToggle,
                     StatusMessage, DataTable, SelectField, CandleChart (+ candle_render.py: dibuja con matplotlib, sin tkinter)
    base/            FormView/FormController (formularios, dibujados dentro de una tarjeta con borde) y PanelView/PanelController (secciones)
    auth/            login, registro y cambio de contraseña temporal (vistas, controladores, pantallas.py)
    shell/           ventana "home": menú lateral + área de contenido (ShellView, ShellController)
    inicio/          sección de bienvenida (PROVISIONAL: se rehace al final)
    mercado/         mercado_view (panel dividido), lista_view/lista_controller, grafico_view/grafico_controller
    admin/           usuarios, activos, ingesta: cada uno con su vista y su controlador;
                     activo_dialogs.py = ventanas emergentes de Activos (agregar y editar)
    <módulo>/        trading/, backtesting/, ia/... cuando lleguen
```
**(previsto)** = la carpeta existe solo con su `__init__.py` y un docstring; se llena cuando llegue su módulo.
Cada módulo de `iu/` tiene su `pantallas.py` con `registrar(navegador)`; `iu/rutas.py` los junta.
El paquete se llama **`simultradia`** (no `main`: chocaría con `main.py`).

### 4.3 Piezas que conviene entender
- **Callbacks:** la vista tiene un "enchufe" vacío (`vincular_acciones(al_algo=...)`) que el controlador conecta
  pasando **su método sin paréntesis**. La vista no depende de ningún controlador concreto. El mismo patrón
  se usa en `ejecutar_en_hilo(trabajo, al_terminar=..., al_fallar=...)`.
- **Hilos:** tkinter solo deja tocar widgets desde el hilo principal. El trabajo lento corre en un hilo; su
  resultado vuelve por una cola que `iniciar_revision(root)` (en `iu/background.py`) vacía cada 100 ms.
  `FormController._ejecutar` y `PanelController._ejecutar` descartan tanto el **éxito como el error** si
  `vista.esta_viva()` es falso (el usuario ya cambió de pantalla).
- **Navegador y shell:** `Navegador.ir_a(nombre, **parametros)` (lo reciben los controladores). Hay pantallas
  **a ventana completa** (login, registro, home) y **secciones** (`en_shell=True`) que se dibujan dentro del área
  de contenido del shell (`home`), con el menú lateral fijo. Cada pantalla se registra con una **fábrica**
  `(padre, navegador, **parametros) -> vista` que arma vista + controlador y usa `navegador.servicios` y
  `navegador.session`. El tamaño de la ventana lo declara cada ruta (`tamano`, `minimo`). Una vista de shell
  expone `contenido` y `marcar_seccion(nombre)`. El menú está en `iu/shell/pantallas.py` (`_MENU`, con marca de
  solo admin: las secciones de admin aparecen bajo "ADMINISTRACIÓN" solo para administradores).
- **Contraseña temporal:** el admin NUNCA ve la contraseña real de nadie. `UsuarioAdminService.restablecer_password`
  genera una temporal (10 caracteres sin letras que se confunden), guarda solo su hash con `debe_cambiar_password = TRUE`
  y la devuelve UNA vez para que el admin se la entregue (la vista la muestra y la copia al portapapeles). No se aplica a
  administradores. Al iniciar sesión con la temporal, `LoginController` NO abre la sesión: manda a la pantalla
  `cambiar_password` (pide la temporal otra vez, la nueva y la confirmación) y, al cambiarla, vuelve al login.
  `UsuarioService.cambiar_password_temporal` solo funciona si la cuenta tiene un cambio pendiente.
- **Sesión:** `Session` (en `core`) guarda el usuario actual. **La crea `App` (una sola) y se inyecta** al Navegador
  y a los controladores que la necesitan; no hay singleton global. El servicio **solo autentica y devuelve el usuario**
  (`autenticar`); el **controlador abre la sesión** cuando el resultado llega a una pantalla vigente.
- **Errores:** todos los esperados heredan de `ErrorAplicacion` (su mensaje se puede mostrar tal cual):
  `DatosInvalidos` (lleva `{campo: mensaje}` y el controlador lo reparte **bajo cada campo**), `ErrorPermisos`,
  `ErrorOperacionInvalida` (una acción que no se puede hacer), `ErrorServicioExterno` (falló una API de afuera),
  `ErrorBaseDatos`, `CredencialesInvalidas`, `CuentaDesactivada`. Los errores que no son de un campo van al
  **mensaje general**. Cualquier otra excepción es inesperada: se registra en el log y el usuario ve un mensaje
  genérico. Las claves de campo (`"nombre"`, `"email"`, `"password"`, `"ticker"`...) son compartidas entre servicio y vista.
- **Permisos:** los métodos de administración reciben `actor: Usuario` (el controlador pasa `session.usuario`) y
  llaman a `exigir_admin(actor)` (`services/permisos.py`), que lanza `ErrorPermisos`.
- **Transacciones:** `with db.obtener_conexion() as conn:` presta una conexión; commit al salir bien, rollback
  si falla, y siempre la devuelve al pool. Todo lo hecho dentro es una sola operación (p. ej. el registro crea
  el usuario y su cuenta simulada juntos). **Nunca se llama a una API externa con una conexión abierta.**
- **Estilos y componentes:** todo componente es una **clase**. Fuentes, colores y espacios salen solo de
  `iu/styles.py` (`Fonts` por rol con la familia en `Fonts.FAMILY`; `Palette` para el gráfico y las etiquetas de la
  tabla). Nunca se escriben a mano.
- **Errores bajo cada campo:** `FormField` incluye un `StatusMessage` oculto que **no ocupa espacio** hasta tener
  texto (tira invisible de 1 px porque Tk no recalcula el tamaño de un contenedor vacío), usa **todo el ancho
  disponible** y se oculta cuando el texto del campo cambia (`StringVar.trace_add`, no `<KeyRelease>`).
- **Tarjeta de los formularios:** `FormView` dibuja el formulario dentro de una tarjeta centrada con un borde de 1 px
  (`Colors.MUTED`); la ventana de fondo usa `Colors.SURFACE` (más claro que la tarjeta), para que el formulario no
  parezca ocupar toda la pantalla al agrandarla. Los widgets internos mantienen el fondo normal del tema.
- **Ventanas emergentes (Activos):** agregar y editar un activo se hacen en ventanas modales (`iu/admin/activo_dialogs.py`:
  `AgregarActivoDialog`, `EditarActivoDialog`) para no recargar la zona sobre la tabla. Son vistas pasivas que abre
  `ActivosAdminView`; la vista conserva la misma interfaz hacia el controlador y reenvía a la ventana abierta los errores
  por campo, los mensajes y el estado «ocupado». Al agregar con éxito la ventana se cierra; doble clic en una fila abre la edición.
- **Probar y actualizar por fuente:** `IngestaService.probar_fuente` le pide a la fuente el precio de su activo de
  ejemplo (`EJEMPLO_TICKER` del cliente) y mide cuánto tarda, sin guardar nada; un fallo se devuelve como resultado, no
  como error. `ejecutar_manual(actor, id_fuente)` actualiza solo una fuente (debe estar habilitada).
  `ActivoAdminService.probar_ticker` comprueba, sin guardar, que una fuente reconoce un ticker (al agregar y antes de
  cambiar la fuente de un activo). Las pantallas de admin con tablas (Usuarios, Activos) tienen buscador y filtros que
  se aplican en el servicio.
- **Fuentes de datos e ingesta:** cada activo tiene una fuente (`activos.id_fuente` → `fuentes_datos`; Binance para
  cripto, Yahoo Finance para el resto). `fuentes_datos.nombre` enlaza la fila con su cliente en `composition.py`.
  `IngestaService` agrupa los activos por fuente y le pide a cada cliente lo suyo **a su propio ritmo**
  (Binance: precios cada 2 s y velas cada 60 s; Yahoo: 30 s y 300 s). Si una fuente o un activo falla, se registra y
  los demás siguen. Una fuente deshabilitada no se consulta. Guardar velas = borrar el rango e insertar, en una
  transacción (9.3 no tiene `ON CONFLICT`).
- **Intervalos y cotización:** la cotización (`cotizaciones_actuales`, UNA fila por activo) **no depende del
  intervalo**; operar siempre será al precio actual. Las velas se guardan para 15 m (60 días), 1 h (365) y 1 d
  (1825). **4 h y 1 sem no se guardan:** se arman agrupando 1 h y 1 d. Config en `domain/reglas/intervalos.py`.
- **"Tiempo real":** el worker escribe el precio en la base cada pocos segundos; la interfaz lo lee cada 2 s (gráfico)
  o 3 s (lista). No hay websocket. La vela en vivo es la última vela guardada con el precio de ahora aplicado
  (`analisis.velas.aplicar_precio`). Solo la cripto abre velas nuevas en vivo; en acciones, ETF e índices el precio
  llega con retraso y, con el mercado cerrado, no se dibujan velas planas.
- **Mercado (pantalla):** un panel dividido (`ttk.PanedWindow`): la lista de activos a la izquierda (buscador,
  categoría, pestañas Todos/Suben/Bajan/Volumen, tabla ordenable) y el gráfico a la derecha. Un clic en la lista
  muestra el gráfico. El borde se arrastra y un botón oculta o muestra la lista. Dos controladores
  (`ListaController`, `GraficoController`) se enlazan en `iu/mercado/pantallas.py`: la lista avisa cuál activo se eligió.
  Cada petición lleva un número y las respuestas viejas (otra búsqueda, otro activo u otro intervalo) se descartan.
- **Gráfico:** `CandleChart` (Tk) usa `candle_render.dibujar_velas` (matplotlib, sin Tk, probable en pruebas).
  Arriba, velas + SMA 20, EMA 50 y Bollinger; debajo, solo si se piden, volumen, RSI 14 y MACD (12, 26, 9). Los
  interruptores y la cantidad de velas (30 a 500) solo cambian el dibujo, no piden nada al servicio. Los parámetros
  están en `domain/reglas/indicadores.py`. Los cálculos usan `float` solo para dibujar; el dinero sigue en `Decimal`.

### 4.4 Para agregar una pantalla
**Formulario:**
1. Vista que hereda de `FormView`: `_agregar_campo(clave, campo)`, `_agregar_mensaje()`,
   `_agregar_boton_principal(...)` y un `vincular_acciones(...)`.
2. Controlador que hereda de `FormController`: conecta las acciones y llama a `self._ejecutar(trabajo, al_terminar=...)`.
3. Servicio con la lógica y las validaciones; repositorio con el SQL; entidad si hay un concepto nuevo; y las tablas o columnas nuevas en la base real (se toma `schema.sql` como guía y se ajusta).
4. En el `pantallas.py` del módulo, una fábrica y su `registrar` (`navegador.registrar("nombre", fabrica, ...)`).

**Sección del panel** (mercado, portafolio, administración...): carpeta `iu/<módulo>/` con vista (hereda de
`PanelView`: título, mensaje general, `esta_viva()` y `programar(ms, accion)` para refrescos que se cancelan solos),
controlador (hereda de `PanelController`: `_ejecutar` descarta resultados de pantallas cerradas y muestra errores) y
`pantallas.py` registrando con `en_shell=True`; sumar el módulo en `iu/rutas.py` y su botón en `_MENU` de
`iu/shell/pantallas.py`. Los refrescos periódicos se encadenan con `vista.programar` y comprueban `esta_viva()`.

---

## 5. Convenciones

**Nombres.** Carpetas, archivos y clases **estructurales en inglés** (`usuario_entity.py`, `UsuarioService`,
`LoginController`, `Database`, `Session`, `Navegador`). Nombres **de negocio, métodos, parámetros y variables en español**
(`iniciar_sesion`, `buscar_por_email`, `obtener_conexion`, `mostrar_error`, `establecer_ocupado`). Archivos en
`snake_case` con sufijo de capa (`_entity`, `_repository`, `_service`, `_view`, `_controller`, `_client`); clases en
`PascalCase`; constantes en `MAYUSCULAS`; privados con `_`; callbacks con prefijo `al_`. Un nombre debe decir
lo que hace: `autenticar` verifica y no inicia sesión; el controlador es quien la inicia.
**Base de datos:** clave primaria `id_<entidad>` y las foráneas con el mismo nombre (`usuarios.id_usuario`,
`cuentas_simuladas.id_usuario`, `activos.id_fuente`).

**Código.**
- Dinero con `Decimal`, nunca `float`. SQL siempre con parámetros. Filas leídas por nombre, nunca por posición.
- Compatible con Python 3.8. Comentarios y docstrings en español, explicando el porqué.
- Cada carpeta de código tiene su `__init__.py`.
- **Un valor que se usa en un solo lugar va en línea, donde se usa.** Solo suben a `settings.py` los valores que
  cambian por entorno (base de datos) o se usan en varios sitios, a `styles.py` los tokens usados 2 o más veces, y a
  `domain/reglas` los parámetros que comparten varias capas (intervalos, indicadores).
- Los tickers se escriben como los entiende su fuente (`BTC/USDT`, `AAPL`, `EURUSD=X`, `^GSPC`).

**Dónde va cada cosa.**
| Si es... | Va en... |
|---|---|
| Dibujar un widget o leer lo escrito | Vista |
| Reaccionar a un evento y decidir (llamar, mostrar error, navegar, abrir/cerrar sesión, refrescar) | Controlador |
| Regla de negocio o **validación** | Servicio, en funciones pequeñas por campo |
| SQL | Repositorio |
| Concepto del negocio / lista cerrada de valores | `domain/entities` / `domain/enums.py` |
| Regla o parámetro puro usado en varios módulos | `domain/reglas` |
| Cálculo numérico sobre series o velas | `analisis/` |
| Llamada a una API externa | `clients/` |
| Tarea programada del worker | `jobs/` |
| Algo técnico reutilizable | `core/` |
| Fuente, color o espaciado compartido | `iu/styles.py` |
| Cómo se escribe un número, fecha o nombre en pantalla | `iu/formato.py` |

---

## 6. Decisiones de diseño (no reabrir sin motivo)

1. **Controladores como intermediarios** y vistas pasivas; el servicio no sabe que existen pantallas. Permite probar los controladores sin ventanas.
2. **Validaciones en el servicio, por campo y reutilizables** (`_error_nombre`, `_error_email`, `_error_password`, `_error_confirmacion`...), combinadas por caso de uso; `lanzar_si_hay_errores` (en `services/validacion.py`) avisa de **todos** los problemas a la vez. **Sin archivo externo de reglas.** (`UsuarioService` conserva su propia copia del método; se unifica cuando se renombre.)
3. **El login valida el formato del email pero no el largo de la contraseña:** esa regla es para elegir una, no para entrar. La confirmación de contraseña también se valida en el servicio.
4. **Seguridad del login:** si el email no existe se hace una verificación de relleno (`gastar_tiempo_de_verificacion`); la **cuenta desactivada se avisa después** de comprobar la contraseña.
5. **Sesión inyectada, no global;** servicio sin efectos secundarios; el controlador abre la sesión solo si la pantalla sigue vigente.
6. **Ajustes mínimos:** `settings.py` solo tiene `app` y `database`. Tema (`app.py`), tamaño de ventana (cada `pantallas.py`), pool de conexiones y reglas de longitud están en línea donde se usan.
7. **Fuentes y demás estilos en `styles.py`;** una sola línea (`Fonts.FAMILY`) cambia la fuente de toda la app.
8. **Clases base `FormView` y `FormController`** (en `iu/base/`) para los formularios, y **`PanelView` y `PanelController`** para las secciones; los componentes son clases. El título y subtítulo del formulario los dibuja `FormView`.
9. **Errores de campo bajo su campo,** ocultos sin ocupar espacio, a todo el ancho y que desaparecen al escribir.
10. **`psycopg2` y `BIGSERIAL`/`JSON`** por PostgreSQL 9.3; contraseñas con argon2.
11. **El registro público solo crea usuarios normales** y crea su cuenta simulada (capital inicial 10 000 USD) **en la misma transacción**. El administrador (creado por script) no tiene cuenta simulada.
12. **`worker.py` separado** (sin ventanas, mismos servicios y repositorios vía `composition.crear_servicios`, misma BD). Hoy mantiene precios y velas; luego evaluará predicciones y órdenes pendientes. Usa un bucle simple, no APScheduler.
13. **Pocos activos y varias categorías:** 5 por categoría (cripto, acción, ETF, divisa, índice y bono) = 30. Cripto desde Binance; el resto desde Yahoo Finance. Los bonos se representan con ETF de bonos (un rendimiento no es un precio operable). Los pares en USDT se tratan como USD. El administrador puede sumar más.
14. **Credenciales de BD en el cliente:** aceptado para un proyecto académico.
15. **Panel de una sola ventana (shell):** tras el login, `home` muestra menú lateral fijo y las secciones se intercambian en el área de contenido; el login usa el mismo Navegador (a ventana completa). Los controladores reciben el `Navegador`, no la `App`.
16. **`App` no arma servicios:** `main.py` crea `Database` y `crear_servicios(db)`; `App` solo recibe los servicios.
17. **`iu/` agrupado por funcionalidad;** el backend, por capas.
18. **Filas por nombre** (`NamedTupleCursor` en `Database`), nunca por índice.
19. **Claves `id_<entidad>`** en todas las tablas.
20. **Servicios por tema, y se separan en dos archivos solo cuando un tema tiene una parte de usuario y otra de administración** (`UsuarioService` + `UsuarioAdminService`, `MercadoService` + `ActivoAdminService`, etc.). No hay un servicio por rol. Las funciones nuevas de usuario (perfil, cambiar contraseña...) irán en `UsuarioService`. **Renombrar `UsuarioService` a `AuthService` queda aplazado hasta terminar el proyecto.**
21. **Migraciones:** descartadas por ahora; la base real se ajusta a mano según se necesite (con scripts SQL sueltos como `mercado_actualizar.sql`, que se pueden borrar después de usarlos).
22. **El esquema SQL es orientativo,** salvo las tablas que ya existen de verdad (sección 7). El código y el usuario mandan sobre `schema.sql`.
23. **Mercado es una sola pantalla de panel dividido** (lista + gráfico, ocultable y con borde arrastrable). No existe una "ficha" aparte. El administrador no opera, pero ve Mercado.
24. **Sin tarjetas de resumen** como recurso por defecto: se muestra la información como texto, filas o tablas.
25. **Las fuentes de datos son datos, no código fijo:** tabla `fuentes_datos`; cada activo apunta a una fuente; el administrador elige la fuente al agregar un activo, puede cambiarla (se borran sus velas y su cotización para no mezclar orígenes) y puede habilitar o deshabilitar una fuente entera. Una fuente nueva = su cliente en `clients/` + su registro en `composition.py` + una fila en `fuentes_datos`.
26. **Tiempo real por consulta a la base** (ver sección 4.3); la ingesta es tolerante: un fallo no frena a los demás.
27. **Indicadores en Python puro** (`analisis/`), parámetros en `domain/reglas/indicadores.py`, dibujo en `candle_render.py`.
28. **El Inicio del usuario se deja para el final** (hoy es una pantalla de bienvenida provisional) para diseñarlo cuando todas las funcionalidades existan.
29. **Contraseña olvidada = contraseña temporal entregada por el admin** (no hay correo ni preguntas secretas): se muestra
    una sola vez, deja de valer la anterior y el usuario debe cambiarla al entrar (columna `usuarios.debe_cambiar_password`).
30. **Ritmo de las fuentes: fijo en el código por ahora** (`segundos_entre_*` de cada cliente). Hacerlo editable desde admin
    está pendiente de decisión (ver sección 10).
31. **Los formularios (login, registro, cambio de contraseña) van dentro de una tarjeta con borde y fondo distinto al de la
    ventana** (`FormView`), para que no parezcan ocupar toda la pantalla al agrandarla.
32. **Agregar y editar un activo (admin) son ventanas emergentes,** no formularios sobre la tabla (`iu/admin/activo_dialogs.py`):
    menos cosas encima de la tabla. Doble clic en una fila abre la edición.
33. **Entrega de cambios: siempre un `.zip` con los archivos nuevos y modificados, sin código para copiar y pegar** (sección 2, punto 3).

---

## 7. Base de datos (PostgreSQL 9.3)

**`database/schema.sql` es una GUÍA de lo que la base podría llegar a tener, no la fuente de verdad.** La base real
tiene hoy estas tablas y se irá ajustando por módulo:

- `usuarios` (recortada: sin `avatar_url`, por ejemplo) y `cuentas_simuladas`.
- **Las de Mercado, definidas de verdad en `database/mercado.sql`:** `fuentes_datos` (`id_fuente`, `nombre`, `activa`),
  `activos` (`id_activo`, `ticker`, `nombre`, `tipo`, `moneda`, `activo`, `id_fuente`, `creado_en`),
  `precios_velas` (`id_activo`, `intervalo`, `momento`, OHLCV; clave compuesta) y `cotizaciones_actuales`
  (`id_activo`, `precio`, `cierre_anterior`, `variacion_pct_dia`, `maximo_dia`, `minimo_dia`, `volumen_dia`,
  `actualizado_en`). Más los tipos `tipo_activo` e `intervalo_vela`. Son más chicas que las de la guía a propósito
  (sin sector, logo, capitalización, etc.).

Lo demás es el diseño orientativo: tablas, columnas y nombres pueden cambiar o no existir. Lo que sí es regla:
PostgreSQL 9.3, claves `id_<entidad>` y los tipos de abajo.

- **Versión 9.3:** `BIGSERIAL`, `JSON`, `COUNT(CASE WHEN ...)`, `EXECUTE PROCEDURE` en triggers, sin `ON CONFLICT` ni `CREATE INDEX IF NOT EXISTS`, sin TimescaleDB.
- **Claves:** PK `id_<entidad>` (`usuarios.id_usuario`, `activos.id_activo`, `cuentas_simuladas.id_cuenta`, `ordenes.id_orden`...); las foráneas llevan el mismo nombre. Índice único `lower(email)`: el email se guarda en minúsculas.
- **Tipos:** dinero `NUMERIC(20,4)`, precios `NUMERIC(20,8)`, cantidades `NUMERIC(28,10)`, porcentajes como número legible (5.25 = 5,25 %), **probabilidades de la IA de 0 a 1**, fechas `TIMESTAMPTZ` en UTC.
- **Ideas clave del modelo (orientativas, aún sin crear):**
  - `ordenes` es la intención del usuario y `ejecuciones` lo que realmente ocurrió; el historial sale de `ejecuciones`.
  - `posiciones` (solo largas) es lo que posee ahora; al vender todo se borra la fila y se registra en `operaciones_cerradas`.
  - `snapshots_portafolio` es la foto diaria del patrimonio.
  - `sesiones_replay` usa una cuenta propia con `es_replay = TRUE`.
  - `predicciones_direccion` guarda lo predicho y lo ocurrido (`acierto`); `vista_precision_modelos` calcula el historial.
  - `estrategias.definicion` (JSON) guarda las reglas del backtesting.
  - `registros_ingesta` (errores por activo y ejecución) y `auditoria_admin` quedan para cuando se amplíe la administración.
- **Fuera del esquema (descartadas):** configuraciones de gráfico, datos fundamentales, calendario de eventos, chat asistente, tutoriales y retos, y posiciones cortas. No hay enums ni columnas para ellas.
- **Compra/venta vs. larga/corta:** `ordenes.lado` (`compra`/`venta`) sí existe; `posiciones` no tiene `lado` porque solo hay posiciones largas (vender cierra o reduce la posición).
- **Vistas y función (guía):** `vista_posiciones_valoradas`, `vista_resumen_cuenta`, `vista_estadisticas_operaciones`, `vista_precision_modelos`, `reiniciar_cuenta(id_cuenta)`.

---

## 8. Pruebas

- Desde la raíz: `python -m unittest discover -s tests -t . -v` (con `pip install -e .` hecho). No necesitan PostgreSQL, ventanas ni internet.
- Estructura: `tests/fakes.py` (falsos compartidos) y subcarpetas `core/`, `services/`, `iu/`, `analisis/`, `clients/`, cada una con `__init__.py`; se importa `from tests.fakes import ...`.
- **Servicios:** `DatabaseFalsa`, `RepositorioFalso`, `CuentaRepositorioFalso`, `RepoActivoFalso`, `RepoPrecioFalso`, `RepoFuenteFalso`, `UsuarioRepoAdminFalso`, `ClienteMercadoFalso` (hace de una fuente y declara sus tipos, formato de ticker y ritmo).
- **Controladores:** `VistaFalsa` (formularios), `VistaPanelFalsa` (secciones; anota lo que le ordenan), `NavegadorFalso`, `ServicioFalso`, `ServicioGenerico` (responde cualquier método con lo que se le prepare) y una `Session()` propia por prueba. `ejecutar_en_hilo` se reemplaza con `mock.patch(...)` en `simultradia.iu.base.form_controller` o `simultradia.iu.base.panel_controller` (en el acto, o diferido con `EjecutorDiferido`).
- **Navegador:** `VentanaFalsa`, `PantallaFalsa`, `ShellFalso`.
- **Análisis, formato y gráfico:** puro Python; el dibujo (`candle_render`) se prueba con una `Figure` de matplotlib y `savefig`. Las pruebas del cliente de Yahoo usan tablas de pandas armadas a mano (se saltan si pandas no está).
- **Entorno de Claude:** sin tkinter, ttkbootstrap, psycopg2, ccxt, yfinance ni red. Se verifica con módulos simulados (stubs) en una carpeta temporal y `PYTHONPATH`. Lo visual y las conexiones reales solo los puede comprobar el usuario.

---

## 9. Qué evitar

Archivos de "reglas" o "validaciones" externos · singletons globales · SQL fuera de repositorios · lógica en
vistas · tkinter en servicios o en `core` · componentes como funciones · `float` para dinero · ajustes, estilos o
tokens para valores de un solo uso · fuentes, colores o espacios escritos a mano en vistas o componentes ·
filas leídas por posición · `sys.path.insert` · sobrescribir un archivo sin ver antes su estado actual ·
afirmar que algo funciona visualmente sin haberlo visto · tarjetas de resumen donde una línea o una tabla bastan ·
llamar a una API externa con una conexión de base de datos abierta · mezclar velas de dos fuentes en un mismo activo ·
dibujar velas planas con el mercado cerrado · una consulta SQL distinta por cada combinación de filtros cuando hay
pocas filas · un servicio por rol en lugar de por tema · **entregar código para copiar y pegar en lugar del `.zip`**.

---

## 10. Estado actual y pendientes

**Hecho**
- Login, registro, shell con menú lateral y sección de Inicio provisional. Formularios dentro de una tarjeta con borde.
- **Mercado:** 30 activos de 6 categorías, lista filtrable y ordenable, gráfico de velas casi en tiempo real con
  intervalos 15 m / 1 h / 4 h / 1 d / 1 sem, cantidad de velas elegible e indicadores SMA, EMA, Bollinger, volumen,
  RSI y MACD.
- **Datos:** worker con ingesta por fuente (Binance y Yahoo Finance), cada una a su ritmo.
- **Administración:** Usuarios (buscar y filtrar, activar/desactivar, restablecer contraseña con una temporal), Activos
  (buscar y filtrar, agregar y editar en ventanas emergentes, probar ticker, habilitar, probar y cambiar fuente) e
  Ingesta de datos (estado, habilitar fuentes, probar conexión, actualizar una fuente o todo).

**Pendiente de administración (próxima mejora)**
- Usuarios: **cambiar el rol** (decidido a medias: ver más abajo), reiniciar la cuenta (necesita las tablas de operar) y
  ver el detalle de un usuario (su cuenta simulada, solo lectura).
- Activos: estado de los datos por activo ("al día", "desactualizado", "sin datos") y botón para recargar las velas de uno solo.
- Fuentes e ingesta: historial de errores guardado en una tabla (`registros_ingesta`), **ritmo editable por fuente**
  (requiere 2 columnas en `fuentes_datos`, límites mínimos por fuente para no ser bloqueado, y no cambia el refresco de la
  pantalla, que sigue siendo de 2-3 s), y mantenimiento (borrar velas antiguas).
- Auditoría de acciones del administrador, revalidar al `actor` contra la base en cada acción de admin (hoy se confía en el
  usuario guardado en la sesión), modelos de IA, glosario y panel de resumen.
- **Cambiar el rol — propuesta pendiente de aprobar:** al ascender a un usuario su cuenta simulada se CONSERVA sin usarse
  (el admin no opera, y los servicios lo exigen; no se borra nada); al volver a usuario se reutiliza esa cuenta, y si nunca
  tuvo una (se creó como admin) se crea una nueva con el capital inicial en la misma transacción. No se puede cambiar el
  rol propio ni dejar al sistema sin ningún admin.

**Pendiente del usuario (orden propuesto)**
Operar y Portafolio (van juntos) → Watchlist → noticias → IA → Backtesting → Replay → Coach → Glosario → **Inicio** (al final).

**Deuda técnica conocida**
- Renombrar `UsuarioService` a `AuthService` y usar `validacion.py` en lugar de su copia de `_lanzar_si_hay_errores` (aplazado al final del proyecto).
- `yfinance` no se ha probado contra internet real; Yahoo cambia y bloquea con cierta frecuencia. Si falla, el worker lo registra y sigue con Binance.
- Binance puede estar bloqueado en algunos países; si no hay datos, revisar el log del worker.
- Lo visual de la interfaz nunca lo ha visto Claude: lo valida el usuario ejecutando la app (incluidas la tarjeta de los formularios y las ventanas emergentes de Activos).
