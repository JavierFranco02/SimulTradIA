"""Una vela (OHLCV): lo que pasó con el precio durante un periodo."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class Vela:
    momento: datetime        # inicio de la vela, en UTC
    apertura: Decimal
    maximo: Decimal
    minimo: Decimal
    cierre: Decimal
    volumen: Decimal
