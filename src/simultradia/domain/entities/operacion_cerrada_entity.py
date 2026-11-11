"""Una venta ya hecha, con su ganancia (espejo de la tabla operaciones_cerradas)."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class OperacionCerrada:
    id_cuenta: int
    id_activo: int
    cantidad: Decimal
    precio_entrada: Decimal
    precio_salida: Decimal
    comisiones: Decimal                      # las de entrada (proporcional) + la de salida
    ganancia_realizada: Decimal              # ya descontadas las comisiones
    abierta_en: Optional[datetime]
    cerrada_en: datetime
    id_operacion_cerrada: Optional[int] = None
