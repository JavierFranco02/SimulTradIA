"""Un activo del catálogo (espejo de la tabla activos)."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from simultradia.domain.enums import TipoActivo


@dataclass
class Activo:
    ticker: str                              # como lo entiende su fuente: "BTC/USDT" (Binance), "AAPL" (Yahoo)
    nombre: str
    tipo: TipoActivo = TipoActivo.CRIPTO
    moneda: str = "USD"                      # moneda en que está el precio (los pares USDT cuentan como USD)
    activo: bool = True                      # False = ya no se actualiza ni se muestra
    id_activo: Optional[int] = None          # lo asigna PostgreSQL al insertar
    creado_en: Optional[datetime] = None
    id_fuente: Optional[int] = None          # de dónde vienen sus precios (tabla fuentes_datos)
    fuente: Optional[str] = None             # nombre de esa fuente ("Binance", "Yahoo Finance")
