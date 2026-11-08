"""Lo que una cuenta posee ahora de un activo (espejo de la tabla posiciones). Solo posiciones largas."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class Posicion:
    id_cuenta: int
    id_activo: int
    cantidad: Decimal
    precio_promedio_entrada: Decimal         # promedio ponderado de lo pagado, SIN comisiones
    comisiones_pagadas: Decimal = Decimal("0")   # comisiones de compra de lo que aún se tiene
    abierta_en: Optional[datetime] = None
    id_posicion: Optional[int] = None        # lo asigna PostgreSQL al insertar
    stop_loss: Optional[Decimal] = None      # vende todo si el precio cae hasta aquí
    take_profit: Optional[Decimal] = None    # vende todo si el precio sube hasta aquí
