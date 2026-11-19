"""Features y etiqueta para predecir la dirección del precio. Python puro, sin BD ni interfaz.

Cada fila de features solo usa datos hasta la vela `i` (nunca del futuro). La etiqueta sí mira
`horizonte` velas adelante: es lo que se quiere predecir. Reutiliza `analisis.indicadores`.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Sequence

from simultradia.analisis.indicadores import atr, bollinger, ema, macd, rsi, sma
from simultradia.domain.entities.vela_entity import Vela
from simultradia.domain.reglas.intervalos import SEGUNDOS
from simultradia.domain.enums import IntervaloVela
from simultradia.domain.reglas.prediccion import (
    ALCISTA, BAJISTA, FACTOR_UMBRAL, LATERAL, VENTANA_VOLATILIDAD)

NOMBRES_FEATURES = (
    "ret_1d", "ret_3d", "ret_5d", "ret_10d", "ret_20d",
    "rsi_14", "macd_hist", "dist_sma20", "dist_ema50", "pos_bollinger",
    "atr_rel", "volatilidad_20d", "volumen_rel", "rango_dia",
)

# Primera vela con todos los indicadores disponibles (la EMA 50 es la que más tarda).
_ARRANQUE = 50


def volatilidad(cierres: Sequence[float], ventana: int = VENTANA_VOLATILIDAD) -> List[Optional[float]]:
    """Desviación estándar de los retornos diarios de las últimas `ventana` velas."""
    n = len(cierres)
    resultado: List[Optional[float]] = [None] * n
    retornos = [cierres[i] / cierres[i - 1] - 1.0 if cierres[i - 1] else 0.0 for i in range(1, n)]
    for i in range(ventana, n):
        parte = retornos[i - ventana:i]            # retornos de las velas i-ventana+1 .. i
        media = sum(parte) / ventana
        resultado[i] = (sum((r - media) ** 2 for r in parte) / ventana) ** 0.5
    return resultado


def umbral_de(vol: float, horizonte: int, factor: float = FACTOR_UMBRAL) -> float:
    """Retorno mínimo (en valor absoluto) para llamar alcista o bajista a un movimiento."""
    return factor * vol * (horizonte ** 0.5)


def etiquetar(cierres: Sequence[float], horizonte: int,
              factor: float = FACTOR_UMBRAL) -> List[Optional[int]]:
    """Clase real de cada vela: BAJISTA, LATERAL o ALCISTA según el retorno a `horizonte` velas
    contra el umbral. None si falta futuro (últimas velas) o no hay volatilidad todavía."""
    n = len(cierres)
    vol = volatilidad(cierres)
    resultado: List[Optional[int]] = [None] * n
    for i in range(n - horizonte):
        if vol[i] is None or not cierres[i]:
            continue
        retorno = cierres[i + horizonte] / cierres[i] - 1.0
        umbral = umbral_de(vol[i], horizonte, factor)
        resultado[i] = ALCISTA if retorno > umbral else BAJISTA if retorno < -umbral else LATERAL
    return resultado


def calcular_features(velas: Sequence[Vela]) -> List[Optional[List[float]]]:
    """Una fila de `NOMBRES_FEATURES` por vela; None mientras falte historia (primeras 50)."""
    n = len(velas)
    c = [float(v.cierre) for v in velas]
    mx = [float(v.maximo) for v in velas]
    mn = [float(v.minimo) for v in velas]
    vo = [float(v.volumen) for v in velas]

    rsi14 = rsi(c, 14)
    hist = macd(c)[2]
    media20, sup, inf = bollinger(c, 20)
    media_20 = sma(c, 20)
    ema50 = ema(c, 50)
    rango_medio = atr(mx, mn, c, 14)
    vol20 = volatilidad(c)
    vol_media = sma(vo, 20)

    filas: List[Optional[List[float]]] = [None] * n
    for i in range(_ARRANQUE, n):
        partes = (rsi14[i], hist[i], media_20[i], ema50[i], sup[i], inf[i],
                  rango_medio[i], vol20[i], vol_media[i])
        if any(p is None for p in partes) or not c[i]:
            continue
        ancho = sup[i] - inf[i]
        filas[i] = [
            c[i] / c[i - 1] - 1.0,
            c[i] / c[i - 3] - 1.0,
            c[i] / c[i - 5] - 1.0,
            c[i] / c[i - 10] - 1.0,
            c[i] / c[i - 20] - 1.0,
            rsi14[i] / 100.0,
            hist[i] / c[i],
            c[i] / media_20[i] - 1.0,
            c[i] / ema50[i] - 1.0,
            (c[i] - inf[i]) / ancho if ancho else 0.5,
            rango_medio[i] / c[i],
            vol20[i],
            vo[i] / vol_media[i] if vol_media[i] else 1.0,
            (mx[i] - mn[i]) / c[i],
        ]
    return filas


def velas_cerradas(velas: Sequence[Vela], ahora: Optional[datetime] = None,
                   intervalo: IntervaloVela = IntervaloVela.D1) -> List[Vela]:
    """Quita la vela que todavía está en curso: sus cierre, máximo y volumen aún cambian."""
    ahora = ahora or datetime.now(timezone.utc)
    if ahora.tzinfo is None:
        ahora = ahora.replace(tzinfo=timezone.utc)
    duracion = timedelta(seconds=SEGUNDOS[intervalo])
    cerradas = []
    for v in velas:
        inicio = v.momento if v.momento.tzinfo else v.momento.replace(tzinfo=timezone.utc)
        if inicio + duracion <= ahora:
            cerradas.append(v)
    return cerradas
