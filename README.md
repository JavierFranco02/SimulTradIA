# SimulTradIA

Aplicación de escritorio (Python + ttkbootstrap + PostgreSQL). Por ahora incluye login, registro y el panel principal (shell) con la sección de inicio.

## Requisitos
- Python 3.8 o superior
- PostgreSQL 9.3 o superior

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
3. Copia `.env.example` como `.env` y completa los datos de tu PostgreSQL.
4. Crea tu cuenta de administrador (una sola vez):
   ```
   python scripts/crear_admin.py
   ```
5. Ejecuta la aplicación:
   ```
   python main.py
   ```

## Pruebas
```
python -m unittest discover -s tests -t . -v
```

## Dónde cambiar cosas
- **Fuente de toda la app, tamaños de fuente, colores y espaciados:** `src/simultradia/iu/styles.py`
- **Tema de la ventana:** `src/simultradia/app.py`; **tamaño de cada pantalla:** su `pantallas.py` (`iu/auth/`, `iu/shell/`)
- **Datos de la base de datos:** el archivo `.env`
- **Reglas de validación (largo de contraseña, formato de email...):** `src/simultradia/services/usuario_service.py`
- **Menú lateral del panel:** `src/simultradia/iu/shell/pantallas.py`
