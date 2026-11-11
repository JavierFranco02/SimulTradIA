"""La cuenta con dinero virtual de un usuario (espejo de la tabla cuentas_simuladas)."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class CuentaSimulada:
    id_usuario: int
    nombre: str
    capital_inicial: Decimal                 # dinero siempre con Decimal, nunca float
    saldo_disponible: Decimal
    moneda: str = "USD"
    id_cuenta: Optional[int] = None          # lo asigna PostgreSQL al insertar
    creada_en: Optional[datetime] = None
    comision_pct: Decimal = Decimal("0.1")       # número legible: 0.1 = 0,1 % por operación
    deslizamiento_pct: Decimal = Decimal("0")    # 0 = se ejecuta al precio exacto; 0.05 = 0,05 % peor
