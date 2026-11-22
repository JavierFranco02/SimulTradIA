"""Features y objetivo para predecir la volatilidad (el rango del día siguiente). Python puro, sin BD ni interfaz.

Cada fila de features usa solo datos hasta la vela `i`. El objetivo SÍ mira el futuro: es
ln(rango de la vela i+h) - ln(rango normal de la vela i), o sea cuántas veces lo normal será el próximo día
(en logaritmo). Predecir la razón con lo normal ya descontado hace al modelo independiente de la escala del activo.
"""
import math
from typing import List, Optional, Sequence

from simultradia.domain.entities.vela_entity import Vela
from simultradia.domain.reglas.volatilidad import HORIZONTE, PISO_RANGO, VENTANA_NORMAL, dia_utc

NOMBRES_FEATURES = (
    "lr_hoy", "lr_media_3", "lr_media_5", "lr_media_10", "lr_media_20", "lr_media_60", "lr_media_120",
    "razon_3_20", "razon_20_120",
    "abs_ret_1", "abs_ret_media_5", "abs_ret_media_20", "vol_20", "vol_60",
    "ret_1", "ret_5", "ret_20", "gap_abs", "volumen_rel", "caida_60",
    "dia_sin", "dia_cos",
)
ARRANQUE = 120                     # primera vela con todo calculable (la media de 120 rangos)
INDICE_NORMAL = NOMBRES_FEATURES.index("lr_media_20")


def rango_de(vela: Vela) -> float:
    """(máximo - mínimo) / cierre, con un piso para poder tomar logaritmo."""
    cierre = float(vela.cierre)
    if cierre <= 0:
        return PISO_RANGO
    return max((float(vela.maximo) - float(vela.minimo)) / cierre, PISO_RANGO)


def rangos(velas: Sequence[Vela]) -> List[float]:
    return [rango_de(v) for v in velas]


def _medias(valores: Sequence[float], ventana: int) -> List[Optional[float]]:
    """Media móvil de `ventana` valores terminada en cada posición (None mientras falte historia)."""
    salida: List[Optional[float]] = [None] * len(valores)
    suma = 0.0
    for i, v in enumerate(valores):
        suma += v
        if i >= ventana:
            suma -= valores[i - ventana]
        if i >= ventana - 1:
            salida[i] = suma / ventana
    return salida


def _desviaciones(valores: Sequence[Optional[float]], ventana: int) -> List[Optional[float]]:
    salida: List[Optional[float]] = [None] * len(valores)
    for i in range(ventana, len(valores)):
        parte = valores[i - ventana + 1:i + 1]
        if any(p is None for p in parte):
            continue
        media = sum(parte) / ventana
        salida[i] = (sum((p - media) ** 2 for p in parte) / (ventana - 1)) ** 0.5
    return salida


def rango_normal(velas: Sequence[Vela]) -> List[Optional[float]]:
    """Media de los últimos `VENTANA_NORMAL` rangos, terminada en cada vela."""
    return _medias(rangos(velas), VENTANA_NORMAL)


def calcular_features(velas: Sequence[Vela]) -> List[Optional[List[float]]]:
    """Una fila de `NOMBRES_FEATURES` por vela; None mientras falten las primeras 120."""
    n = len(velas)
    c = [float(v.cierre) for v in velas]
    r = rangos(velas)
    ret: List[Optional[float]] = [None] + [c[i] / c[i - 1] - 1.0 if c[i - 1] else 0.0 for i in range(1, n)]
    absret = [abs(x) if x is not None else None for x in ret]

    medias = {k: _medias(r, k) for k in (3, 5, 10, 20, 60, 120)}
    vo = [float(v.volumen) for v in velas]
    vol_media = _medias(vo, 20)
    abs_media_5 = _medias([a if a is not None else 0.0 for a in absret], 5)
    abs_media_20 = _medias([a if a is not None else 0.0 for a in absret], 20)
    vol20 = _desviaciones(ret, 20)
    vol60 = _desviaciones(ret, 60)

    filas: List[Optional[List[float]]] = [None] * n
    for i in range(ARRANQUE, n):
        if not c[i] or not c[i - 1] or not c[i - 5] or not c[i - 20] or vol20[i] is None or vol60[i] is None:
            continue
        lr = {k: math.log(medias[k][i]) for k in medias}
        maximo_60 = max(c[i - 59:i + 1])
        momento = velas[i].momento
        angulo = 2.0 * math.pi * dia_utc(momento).weekday() / 7.0
        filas[i] = [
            math.log(r[i]), lr[3], lr[5], lr[10], lr[20], lr[60], lr[120],
            lr[3] - lr[20], lr[20] - lr[120],
            absret[i], abs_media_5[i], abs_media_20[i], vol20[i], vol60[i],
            ret[i], c[i] / c[i - 5] - 1.0, c[i] / c[i - 20] - 1.0,
            abs(float(velas[i].apertura) / c[i - 1] - 1.0),
            vo[i] / vol_media[i] if vol_media[i] else 1.0,
            c[i] / maximo_60 - 1.0,
            math.sin(angulo), math.cos(angulo),
        ]
    return filas


def etiquetar(velas: Sequence[Vela], horizonte: int = HORIZONTE) -> List[Optional[float]]:
    """ln(rango de la vela i+h) - ln(rango normal de la vela i). None si falta futuro o historia."""
    n = len(velas)
    r = rangos(velas)
    normal = _medias(r, VENTANA_NORMAL)
    return [math.log(r[i + horizonte]) - math.log(normal[i]) if i + horizonte < n and normal[i] else None
            for i in range(n)]
