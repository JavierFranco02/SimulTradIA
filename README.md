# SimulTradIA

Aplicación de escritorio (Python + ttkbootstrap + PostgreSQL). Incluye login, registro, el panel principal (shell),
**Mercado** (lista de activos y gráfico de velas con indicadores, en un panel dividido) y el panel de
**administración** (usuarios, activos con su fuente de datos, e ingesta). Hay 30 activos: 5 criptomonedas
(Binance) y 25 acciones, ETF, divisas, índices y bonos (Yahoo Finance).

## Requisitos
- Python 3.8 o superior
- PostgreSQL 9.3 o superior
- Conexión a internet (los precios vienen de Binance y Yahoo Finance; no hace falta cuenta ni claves)

## Puesta en marcha

1. Crea un entorno virtual e instala el proyecto (modo editable):
   ```
   python -m venv .venv
   .venv\Scripts\activate        (Windows)
   source .venv/bin/activate     (Linux / macOS)
   pip install -e .
   ```
   (Si pip es muy antiguo: `python -m pip install --upgrade pip`.)
2. Crea la base de datos y sus tablas (`database/schema.sql` es una guía; crea solo las que necesites hoy: `usuarios` y `cuentas_simuladas`):
   ```
   createdb simulador_trading
   psql -d simulador_trading -v ON_ERROR_STOP=1 -f database/schema.sql
   ```
   Para Mercado, crea además sus tablas (`fuentes_datos`, `activos`, `precios_velas`, `cotizaciones_actuales`) y carga los 30 activos:
   ```
   psql -d simulador_trading -v ON_ERROR_STOP=1 -f database/mercado.sql
   ```
   (Si ya habías ejecutado la versión anterior de `mercado.sql`, solo con criptomonedas, ejecuta en cambio
   `database/mercado_actualizar.sql`; después puedes borrar ese archivo.)
3. Copia `.env.example` como `.env` y completa los datos de tu PostgreSQL.
4. Crea tu cuenta de administrador (una sola vez):
   ```
   python scripts/crear_admin.py
   ```
5. En una terminal, deja corriendo el proceso que mantiene los precios al día (la primera vez descarga el historial y tarda unos minutos):
   ```
   python worker.py
   ```
6. En otra terminal, ejecuta la aplicación:
   ```
   python main.py
   ```

## Pruebas
```
python -m unittest discover -s tests -t . -v
```

## Dónde cambiar cosas
- **Fuente de toda la app, tamaños de fuente, colores (incluido el gráfico) y espaciados:** `src/simultradia/iu/styles.py`
- **Tema de la ventana:** `src/simultradia/app.py`; **tamaño de cada pantalla:** su `pantallas.py` (`iu/auth/`, `iu/shell/`)
- **Datos de la base de datos:** el archivo `.env`
- **Reglas de validación (largo de contraseña, formato de email...):** `src/simultradia/services/usuario_service.py`
- **Menú lateral del panel:** `src/simultradia/iu/shell/pantallas.py`
- **Qué intervalos de vela se guardan y cuánta historia:** `src/simultradia/domain/reglas/intervalos.py`
- **Cada cuánto actualiza el worker precios y velas:** `worker.py` (la pasada) y, por fuente, `segundos_entre_cotizaciones` y `segundos_entre_velas` en `clients/binance_client.py` y `clients/yahoo_client.py`
- **Parámetros de los indicadores (SMA, EMA, Bollinger, RSI, MACD):** `src/simultradia/domain/reglas/indicadores.py`
- **Sumar una fuente de datos nueva:** su cliente en `clients/`, registrado en `composition.py`, y una fila en `fuentes_datos`
