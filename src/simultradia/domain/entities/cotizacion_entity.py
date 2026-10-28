"""Último precio de un activo y lo que se arma con él para las pantallas de mercado."""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from simultradia.domain.entities.activo_entity import Activo


@dataclass
class Cotizacion:
    """Espejo de cotizaciones_actuales. No depende del intervalo del gráfico:
    hay UNA por activo y siempre es el precio de ahora."""
    precio: Decimal
    id_activo: Optional[int] = None          # lo pone el servicio al guardar
    cierre_anterior: Optional[Decimal] = None
    variacion_pct_dia: Optional[Decimal] = None   # últimas 24 h, número legible (5.25 = 5,25 %)
    maximo_dia: Optional[Decimal] = None
    minimo_dia: Optional[Decimal] = None
    volumen_dia: Optional[Decimal] = None         # en dólares (USDT)
    actualizado_en: Optional[datetime] = None


@dataclass
class ActivoCotizado:
    activo: Activo
    cotizacion: Optional[Cotizacion] = None  # None mientras no se haya descargado ningún precio


@dataclass
class PanelMercado:
    """Lo que muestra la lista de Mercado en un momento dado."""
    items: List[ActivoCotizado] = field(default_factory=list)   # ya filtrados y ordenados
    actualizado_en: Optional[datetime] = None                  # None = aún no hay precios
