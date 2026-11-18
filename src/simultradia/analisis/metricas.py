"""Métricas de riesgo sobre la curva de capital: caída desde el máximo, volatilidad y ratio de Sharpe.

Python puro, sin BD ni interfaz. Las usa Portafolio y, más adelante, Backtesting: por eso viven aquí y
no en una pantalla. Trabajan con float: sirven para mostrar y comparar, no para dinero.
"""
from datetime import datetime, timezone
from math import sqrt
from statistics import mean, stdev
from typing import Dict, List, Optional, Sequence

DIAS_MINIMOS = 20       # con menos días de historial, la volatilidad y el Sharpe no son confiables
_DIAS_AL_ANO = 365      # la curva se guarda todos los días (la cripto no cierra)


def caidas(valores: Sequence[float]) -> List[float]:
    """Cuánto está cada valor por debajo del máximo alcanzado hasta ahí, en % (0 o negativo).
    Ejemplo: máximo 10 420 y ahora 10 097 -> -3,10."""
    resultado: List[float] = []
    maximo = None
    for valor in valores:
        if maximo is None or valor > maximo:
            maximo = valor
        resultado.append((valor - maximo) / maximo * 100 if maximo else 0.0)
    return resultado


def caida_maxima(valores: Sequence[float]) -> float:
    """La peor caída desde un máximo (drawdown), en % (0 o negativo)."""
    return min(caidas(valores), default=0.0)


def retornos_diarios(momentos: Sequence[datetime], valores: Sequence[float]) -> List[float]:
    """Cuánto subió o bajó el capital de un día al siguiente (0,01 = +1 %). De cada día (UTC) se toma el
    último valor. `momentos` debe venir en orden."""
    ultimo_de_cada_dia: Dict = {}
    for momento, valor in zip(momentos, valores):
        ultimo_de_cada_dia[momento.astimezone(timezone.utc).date()] = valor
    cierres = list(ultimo_de_cada_dia.values())
    return [b / a - 1 for a, b in zip(cierres, cierres[1:]) if a]


def volatilidad_anual(retornos: Sequence[float]) -> Optional[float]:
    """Cuánto se mueve el capital, llevado a un año, en %. None si hay menos de DIAS_MINIMOS días."""
    if len(retornos) < DIAS_MINIMOS:
        return None
    return stdev(retornos) * sqrt(_DIAS_AL_ANO) * 100


def sharpe(retornos: Sequence[float]) -> Optional[float]:
    """Ganancia por cada unidad de riesgo (sin tasa libre de riesgo), llevada a un año.
    None si hay menos de DIAS_MINIMOS días o si el capital no se movió."""
    if len(retornos) < DIAS_MINIMOS:
        return None
    desviacion = stdev(retornos)
    if desviacion == 0:
        return None
    return mean(retornos) / desviacion * sqrt(_DIAS_AL_ANO)
