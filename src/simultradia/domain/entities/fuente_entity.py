"""De dónde vienen los precios de un grupo de activos (espejo de la tabla fuentes_datos)."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Fuente:
    nombre: str                  # clave que enlaza con el cliente del código: "Binance", "Yahoo Finance"
    activa: bool = True          # False = sus activos dejan de actualizarse
    id_fuente: Optional[int] = None
    total_activos: int = 0                           # activos habilitados que usan esta fuente
    ultima_cotizacion: Optional[datetime] = None     # el precio más reciente recibido de ella
