"""Ajustes de la aplicación, agrupados por categoría.

    from simultradia.core.settings import SETTINGS

    SETTINGS.app.name           -> "SimulTradIA"
    SETTINGS.database.host      -> datos de conexión (vienen del .env)

Aquí SOLO van los valores que cambian según el equipo o el entorno (como la
base de datos) o que se usan en varios lugares. Un valor que se usa en un solo
sitio vive junto al código que lo usa, no aquí.

Para agregar una categoría nueva: crea su dataclass y agrégala a `Settings`.
"""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# .../SimulTradIA/src/simultradia/core/settings.py  ->  parents[3] = carpeta del proyecto
PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class AppSettings:
    name: str = "SimulTradIA"


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    name: str
    user: str
    password: str


@dataclass(frozen=True)
class Settings:
    app: AppSettings
    database: DatabaseSettings


def load_settings() -> Settings:
    return Settings(
        app=AppSettings(),
        database=DatabaseSettings(
            host=os.getenv("BD_HOST", "localhost"),
            port=int(os.getenv("BD_PUERTO", "5432")),
            name=os.getenv("BD_NOMBRE", "simulador_trading"),
            user=os.getenv("BD_USUARIO", "postgres"),
            password=os.getenv("BD_PASSWORD", ""),
        ),
    )


SETTINGS = load_settings()
