"""Operaciones puras sobre listas de velas: agrupar y aplicar el precio en vivo.

Sin BD ni interfaz. Todas las velas están en UTC.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List

from simultradia.domain.entities.vela_entity import Vela
from simultradia.domain.enums import IntervaloVela
from simultradia.domain.reglas.intervalos import SEGUNDOS


def inicio_de_periodo(momento: datetime, intervalo: IntervaloVela) -> datetime:
    """Cuándo empieza la vela de `intervalo` que contiene a `momento`.

    Las de 15 m, 1 h, 4 h y 1 d empiezan en múltiplos exactos desde la medianoche UTC.
    La semanal empieza el lunes a las 00:00 UTC (como en Binance).
    """
    if intervalo == IntervaloVela.W1:
        utc = momento.astimezone(timezone.utc)
        lunes = utc - timedelta(days=utc.weekday())
        return lunes.replace(hour=0, minute=0, second=0, microsecond=0)
    segundos = SEGUNDOS[intervalo]
    ts = int(momento.timestamp())
    return datetime.fromtimestamp(ts - ts % segundos, tz=timezone.utc)


def agrupar_velas(velas: List[Vela], intervalo: IntervaloVela) -> List[Vela]:
    """Junta velas pequeñas (ordenadas) en velas de `intervalo`: apertura de la primera,
    máximo más alto, mínimo más bajo, cierre de la última y volumen sumado."""
    grupos: List[Vela] = []
    for vela in velas:
        inicio = inicio_de_periodo(vela.momento, intervalo)
        if grupos and grupos[-1].momento == inicio:
            g = grupos[-1]
            grupos[-1] = Vela(inicio, g.apertura, max(g.maximo, vela.maximo),
                              min(g.minimo, vela.minimo), vela.cierre, g.volumen + vela.volumen)
        else:
            grupos.append(Vela(inicio, vela.apertura, vela.maximo, vela.minimo,
                               vela.cierre, vela.volumen))
    return grupos


def aplicar_precio(velas: List[Vela], precio: Decimal, momento: datetime,
                   intervalo: IntervaloVela, abrir_nuevas: bool = True) -> List[Vela]:
    """Devuelve las velas con el precio de ahora ya aplicado (la vela "en vivo").

    - Si `momento` cae dentro de la última vela: cambia su cierre y, si hace falta, su máximo/mínimo.
    - Si ya pasó su fin y `abrir_nuevas`: abre una vela nueva con ese precio. Es lo correcto para
      mercados que no cierran (cripto). En los que sí cierran (acciones...) se pone False: si no,
      un fin de semana se dibujarían velas planas; la vela nueva llega cuando se descargan las velas.
    - Si el precio es más viejo que la última vela: no toca nada.
    """
    if not velas:
        return velas
    ultima = velas[-1]
    if momento < ultima.momento:
        return velas
    if momento < ultima.momento + timedelta(seconds=SEGUNDOS[intervalo]):
        nueva = Vela(ultima.momento, ultima.apertura, max(ultima.maximo, precio),
                     min(ultima.minimo, precio), precio, ultima.volumen)
        return velas[:-1] + [nueva]
    if not abrir_nuevas:
        return velas
    return velas + [Vela(inicio_de_periodo(momento, intervalo), precio, precio, precio, precio,
                         Decimal("0"))]
