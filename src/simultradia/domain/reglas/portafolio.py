"""Reglas puras de Portafolio: rentabilidad, exposición y estadísticas de las operaciones cerradas.

Python puro (sin BD, sin tkinter, sin red). Dinero con Decimal. Las métricas de la curva de capital
(caída máxima, volatilidad, Sharpe) están en `analisis/metricas.py`.

Operación cerrada = una VENTA (total o parcial). "Ganadora" = ganancia realizada mayor que 0.
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import List, Optional, Sequence

from simultradia.domain.entities.operacion_cerrada_entity import OperacionCerrada
from simultradia.domain.reglas.operaciones import redondear_dinero

_CIEN = Decimal(100)
_PORCENTAJE = Decimal("0.0001")
_RATIO = Decimal("0.01")


def rentabilidad_pct(patrimonio: Decimal, capital_inicial: Decimal) -> Decimal:
    """Lo que se ganó o perdió respecto del capital inicial, en %."""
    if capital_inicial <= 0:
        return Decimal(0)
    return ((patrimonio - capital_inicial) / capital_inicial * _CIEN).quantize(_PORCENTAJE, rounding=ROUND_HALF_UP)


def exposicion_pct(valor_posiciones: Decimal, patrimonio: Decimal) -> Decimal:
    """Qué parte del patrimonio está invertida (el resto es saldo), en %."""
    if patrimonio <= 0:
        return Decimal(0)
    return (valor_posiciones / patrimonio * _CIEN).quantize(_PORCENTAJE, rounding=ROUND_HALF_UP)


def ganancia_pct(operacion: OperacionCerrada) -> Decimal:
    """Ganancia de la operación sobre lo que costó comprar lo vendido (sin contar comisiones), en %."""
    costo = operacion.precio_entrada * operacion.cantidad
    if costo <= 0:
        return Decimal(0)
    return (operacion.ganancia_realizada / costo * _CIEN).quantize(_PORCENTAJE, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class EstadisticasOperaciones:
    """Resumen de las operaciones cerradas. Lo que no se puede calcular (sin operaciones, sin pérdidas...) es None."""
    total: int
    ganadoras: int
    tasa_aciertos: Optional[Decimal]         # % de operaciones ganadoras
    factor_beneficio: Optional[Decimal]      # ganancias totales / pérdidas totales (mayor que 1: se gana más de lo que se pierde)
    ganancia_media: Optional[Decimal]        # promedio de las ganadoras
    perdida_media: Optional[Decimal]         # promedio de las perdedoras (negativo)
    por_operacion: Optional[Decimal]         # promedio de todas
    mejor: Optional[Decimal]
    peor: Optional[Decimal]
    ganancia_total: Decimal
    comisiones: Decimal                      # las de estas operaciones (entrada proporcional + salida)


def _media(valores: List[Decimal]) -> Optional[Decimal]:
    return redondear_dinero(sum(valores, Decimal(0)) / len(valores)) if valores else None


def estadisticas_operaciones(operaciones: Sequence[OperacionCerrada]) -> EstadisticasOperaciones:
    todas = [o.ganancia_realizada for o in operaciones]
    ganancias = [g for g in todas if g > 0]
    perdidas = [g for g in todas if g < 0]
    total = len(todas)
    suma_perdidas = sum(perdidas, Decimal(0))
    return EstadisticasOperaciones(
        total=total,
        ganadoras=len(ganancias),
        tasa_aciertos=(Decimal(len(ganancias)) / total * _CIEN).quantize(_PORCENTAJE, rounding=ROUND_HALF_UP)
        if total else None,
        factor_beneficio=(sum(ganancias, Decimal(0)) / -suma_perdidas).quantize(_RATIO, rounding=ROUND_HALF_UP)
        if perdidas else None,
        ganancia_media=_media(ganancias),
        perdida_media=_media(perdidas),
        por_operacion=_media(todas),
        mejor=max(todas) if todas else None,
        peor=min(todas) if todas else None,
        ganancia_total=sum(todas, Decimal(0)),
        comisiones=sum((o.comisiones for o in operaciones), Decimal(0)),
    )
