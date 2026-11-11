"""Una orden (lo que el usuario pidió) y su ejecución (lo que realmente ocurrió)."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from simultradia.domain.enums import EstadoOrden, LadoOrden, TipoOrden


@dataclass
class Orden:
    """Espejo de la tabla ordenes. `ticker` solo viene al leer el historial."""
    id_cuenta: int
    id_activo: int
    lado: LadoOrden
    tipo: TipoOrden
    estado: EstadoOrden
    cantidad: Decimal
    precio_promedio: Optional[Decimal] = None
    comision_total: Decimal = Decimal("0")
    id_orden: Optional[int] = None           # lo asigna PostgreSQL al insertar
    creada_en: Optional[datetime] = None
    ejecutada_en: Optional[datetime] = None
    ticker: Optional[str] = None
    precio_limite: Optional[Decimal] = None  # órdenes límite: a qué precio se ejecutan
    stop_loss: Optional[Decimal] = None      # niveles que recibe la posición cuando una compra límite se ejecuta
    take_profit: Optional[Decimal] = None
    motivo_rechazo: Optional[str] = None
    cancelada_en: Optional[datetime] = None


@dataclass
class Ejecucion:
    """Espejo de la tabla ejecuciones. `ticker` solo viene al leer el historial."""
    id_orden: int
    id_cuenta: int
    id_activo: int
    lado: LadoOrden
    cantidad: Decimal
    precio: Decimal                          # ya con el deslizamiento aplicado
    comision: Decimal
    ejecutada_en: datetime
    id_ejecucion: Optional[int] = None
    ticker: Optional[str] = None
