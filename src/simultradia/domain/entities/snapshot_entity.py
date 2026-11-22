"""Una foto del patrimonio de una cuenta en un momento (espejo de la tabla snapshots_portafolio)."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class SnapshotPortafolio:
    id_cuenta: int
    momento: datetime                # en UTC
    saldo_disponible: Decimal
    valor_posiciones: Decimal        # lo que valen ahora las posiciones abiertas
    patrimonio_total: Decimal        # saldo + posiciones
