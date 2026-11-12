# SimulTradIA

Simulador de trading e inversión con dinero virtual y precios reales. Aplicación de escritorio hecha con Python, ttkbootstrap y PostgreSQL.

Incluye registro e inicio de sesión, **Mercado** (lista de activos y gráfico de velas con indicadores), **Operar** (órdenes a mercado y límite, stop-loss, take-profit y calculadora de riesgo) y un panel de **administración** (usuarios, activos e ingesta de datos). Hay 30 activos: 5 criptomonedas (Binance) y 25 acciones, ETF, divisas, índices y bonos (Yahoo Finance).

> No es asesoría financiera. Todo el dinero es virtual.

## Requisitos

- Python 3.8 o superior
- PostgreSQL 9.3 o superior
- Conexión a internet (los precios vienen de Binance y Yahoo Finance; no hace falta cuenta ni claves)

## Instalación

### 1. Entorno virtual y dependencias

```
python -m venv .venv
.venv\Scripts\activate          (Windows)
source .venv/bin/activate       (Linux / macOS)
pip install -e .
```

Si pip es muy antiguo: `python -m pip install --upgrade pip`.

### 2. Base de datos

Se usan dos archivos, que deben ejecutarse **en este orden** y sobre una base **vacía**:

- `database/simultradia_esquema.sql`: tablas, tipos, índices y restricciones.
- `database/simultradia_datos.sql`: datos iniciales (fuentes, activos, velas, un usuario administrador y un usuario demo).

Los objetos pertenecen al rol `postgres`, por eso se usa ese usuario.

**Opción A: línea de comandos**

```
createdb -U postgres simulador_trading
psql -U postgres -d simulador_trading -v ON_ERROR_STOP=1 -f database/simultradia_esquema.sql
psql -U postgres -d simulador_trading -v ON_ERROR_STOP=1 -f database/simultradia_datos.sql
```

**Opción B: pgAdmin**

1. Clic derecho en *Databases* → *Create* → *Database…*. Nombre: `simulador_trading`, propietario: `postgres`, codificación: `UTF8`. Guardar.
2. Selecciona la base `simulador_trading` y abre el editor SQL (*Tools* → *Query Tool*).
3. Abre `simultradia_esquema.sql` (icono de carpeta) y ejecútalo (F5).
4. Repite con `simultradia_datos.sql`.
5. Clic derecho en la base → *Refresh* para ver las tablas en *Schemas* → *public* → *Tables*.

Si el archivo de datos falla en pgAdmin (por ejemplo, con errores en líneas `COPY ... FROM stdin`), ejecútalo desde *Tools* → *PSQL Tool* con `\i 'ruta/completa/database/simultradia_datos.sql'`, o usa la opción A.

### 3. Configuración

Copia `.env.example` como `.env` y completa tus datos de PostgreSQL:

```
BD_HOST=localhost
BD_PUERTO=5432
BD_NOMBRE=simulador_trading
BD_USUARIO=postgres
BD_PASSWORD=tu_contraseña
```

## Usuarios incluidos

Los datos iniciales traen dos cuentas para probar la aplicación:

| Rol | Email | Contraseña |
|---|---|---|
| Administrador | `COMPLETAR` | `COMPLETAR` |
| Demo (usuario normal) | `COMPLETAR` | `COMPLETAR` |

Para crear otro administrador: `python scripts/crear_admin.py`. Los usuarios normales también pueden registrarse desde la aplicación.

## Ejecución

Se necesitan dos terminales con el entorno virtual activado.

**Terminal 1: worker.** Mantiene los precios y las velas al día y ejecuta las órdenes pendientes, los stop-loss y los take-profit. Déjalo corriendo mientras uses la app.

```
python worker.py
```

**Terminal 2: aplicación**

```
python main.py
```

Sin el worker, los precios no se actualizan y las órdenes límite, stop-loss y take-profit no se ejecutan. También puedes lanzar una actualización manual desde Administración → Ingesta de datos.

## Pruebas

```
python -m unittest discover -s tests -t . -v
```

No necesitan PostgreSQL, ventanas ni internet.

## Problemas frecuentes

- **«No se pudo conectar con la base de datos»:** revisa que PostgreSQL esté encendido y que los datos de `.env` sean correctos.
- **Precios desactualizados:** confirma que `python worker.py` está corriendo y revisa su log. Binance puede estar bloqueado en algunos países y Yahoo Finance limita las peticiones; si una fuente falla, el worker lo registra y sigue con la otra.
- **Los precios de acciones, ETF e índices** llegan con unos 15 minutos de retraso (limitación de Yahoo Finance).
