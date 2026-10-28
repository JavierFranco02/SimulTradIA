"""Cómo se escriben los números y fechas en pantalla (formato español: 10 000,50).

Python puro (sin tkinter): lo usan todas las vistas que muestren dinero, porcentajes o fechas.
"""
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from simultradia.domain.enums import TipoActivo

_ESPACIO = "\u00a0"   # espacio que no se parte en dos líneas

TIPO_SINGULAR = {TipoActivo.ACCION: "Acción", TipoActivo.CRIPTO: "Cripto", TipoActivo.ETF: "ETF",
                 TipoActivo.DIVISA: "Divisa", TipoActivo.INDICE: "Índice", TipoActivo.BONO: "Bono"}
TIPO_PLURAL = {TipoActivo.ACCION: "Acciones", TipoActivo.CRIPTO: "Criptomonedas", TipoActivo.ETF: "ETF",
               TipoActivo.DIVISA: "Divisas", TipoActivo.INDICE: "Índices", TipoActivo.BONO: "Bonos"}


def _redondear(valor: Decimal, decimales: int = 2) -> Decimal:
    return valor.quantize(Decimal(1).scaleb(-decimales), rounding=ROUND_HALF_UP)


def _numero(valor: Decimal, decimales: int = 2) -> str:
    texto = "{:,.{d}f}".format(_redondear(valor, decimales), d=decimales)
    return texto.replace(",", _ESPACIO).replace(".", ",")


def _signo(valor: Decimal, con_signo: bool) -> str:
    """Pone "+" delante de lo que no es negativo (el "-" ya lo escribe el formato)."""
    return "+" if con_signo and _redondear(valor) >= 0 else ""


def dinero(valor: Decimal, moneda: str = "USD", con_signo: bool = False) -> str:
    return _signo(valor, con_signo) + _numero(valor) + _ESPACIO + moneda


def precio(valor: Decimal) -> str:
    """Precio de un activo: más decimales cuanto más barato es (BTC 67 123,45; DOGE 0,123456)."""
    decimales = 2 if valor >= 100 else 4 if valor >= 1 else 6
    return _numero(valor, decimales)


def porcentaje(valor: Decimal, con_signo: bool = False) -> str:
    return _signo(valor, con_signo) + _numero(valor) + _ESPACIO + "%"


def compacto(valor: Decimal) -> str:
    """Números grandes abreviados: 1 250 000 -> "1,25 M" (K = miles, M = millones, B = miles de millones)."""
    for limite, sufijo in ((Decimal(10) ** 9, "B"), (Decimal(10) ** 6, "M"), (Decimal(10) ** 3, "K")):
        if abs(valor) >= limite:
            return _numero(valor / limite) + _ESPACIO + sufijo
    return _numero(valor, 0)


def hace(momento: Optional[datetime], ahora: Optional[datetime] = None) -> str:
    """"hace 5 s", "hace 3 min"... para decir cuán fresco es un dato."""
    if momento is None:
        return "—"
    ahora = ahora or datetime.now(timezone.utc)
    segundos = max(0, int((ahora - momento).total_seconds()))
    if segundos < 60:
        return "hace %d s" % segundos
    if segundos < 3600:
        return "hace %d min" % (segundos // 60)
    if segundos < 86400:
        return "hace %d h" % (segundos // 3600)
    return "hace %d d" % (segundos // 86400)


def fecha_hora(momento: Optional[datetime]) -> str:
    """Fecha y hora en la zona horaria del equipo."""
    return "—" if momento is None else momento.astimezone().strftime("%d/%m/%Y %H:%M")
