"""Adaptador a Yahoo Finance (librería yfinance): acciones, ETF, divisas, índices y bonos.

SOLO trae datos de afuera, como BinanceCliente. Sin cuenta ni claves. Ojo con lo que NO es:
los precios de acciones, ETF e índices llegan con ~15 minutos de retraso y Yahoo limita las
peticiones, por eso se le pide poco y de a muchos activos a la vez (ver `segundos_entre_*`).
"""
import logging
import math
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Sequence

from simultradia.core.exceptions import ErrorServicioExterno
from simultradia.domain.entities.cotizacion_entity import Cotizacion
from simultradia.domain.entities.vela_entity import Vela
from simultradia.domain.enums import IntervaloVela, TipoActivo

_log = logging.getLogger(__name__)
_INTERVALOS_YAHOO = {IntervaloVela.M15: "15m", IntervaloVela.H1: "1h", IntervaloVela.D1: "1d"}
# Yahoo solo entrega los últimos N días de las velas pequeñas (un poco menos del tope, por seguridad).
_MAX_DIAS = {IntervaloVela.M15: 59, IntervaloVela.H1: 729}


def _decimal(valor, decimales: int = 8) -> Optional[Decimal]:
    """float de pandas -> Decimal; None si falta el dato (NaN)."""
    if valor is None or math.isnan(float(valor)):
        return None
    return Decimal(repr(round(float(valor), decimales)))


def cotizaciones_desde_descarga(descarga, tickers: Sequence[str], ahora: datetime) -> Dict[str, Cotizacion]:
    """Convierte la descarga diaria de yfinance (varios activos) en cotizaciones.

    Precio = último cierre; cierre anterior = el cierre del día previo; el volumen se pasa a
    dólares (acciones x precio) para poder compararlo con el de las criptomonedas."""
    resultado: Dict[str, Cotizacion] = {}
    for ticker in tickers:
        columnas = descarga.columns
        if hasattr(columnas, "get_level_values") and ticker in columnas.get_level_values(0):
            tabla = descarga[ticker]
        elif ticker in columnas:     # descarga de un solo activo, sin nivel de ticker
            continue
        else:
            tabla = descarga if len(tickers) == 1 else None
        if tabla is None or "Close" not in tabla:
            continue
        cierres = tabla["Close"].dropna()
        if cierres.empty:
            continue
        precio = _decimal(cierres.iloc[-1])
        anterior = _decimal(cierres.iloc[-2]) if len(cierres) >= 2 else None
        fila = tabla.loc[cierres.index[-1]]
        volumen = _decimal(fila.get("Volume"), 4)
        resultado[ticker] = Cotizacion(
            precio=precio,
            cierre_anterior=anterior,
            variacion_pct_dia=_decimal((precio - anterior) / anterior * 100, 4) if anterior else None,
            maximo_dia=_decimal(fila.get("High")),
            minimo_dia=_decimal(fila.get("Low")),
            volumen_dia=volumen * precio if volumen is not None else None,
            actualizado_en=ahora,
        )
    return resultado


def _momento(marca, intervalo: IntervaloVela) -> datetime:
    """Marca de tiempo de pandas -> datetime UTC. Las velas diarias se fijan a la medianoche UTC
    de su fecha (Yahoo las pone en la hora de la bolsa, lo que desalinearía el día)."""
    if intervalo == IntervaloVela.D1:
        return datetime(marca.year, marca.month, marca.day, tzinfo=timezone.utc)
    momento = marca.to_pydatetime()
    return (momento if momento.tzinfo else momento.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def velas_desde_historial(historial, intervalo: IntervaloVela) -> List[Vela]:
    """Convierte la tabla de yfinance en velas válidas (sin huecos ni repetidas)."""
    por_momento: Dict[datetime, Vela] = {}
    for marca, fila in historial.iterrows():
        valores = [_decimal(fila.get(c)) for c in ("Open", "High", "Low", "Close")]
        if any(v is None for v in valores):
            continue
        apertura, alto, bajo, cierre = valores
        momento = _momento(marca, intervalo)
        por_momento[momento] = Vela(
            momento=momento, apertura=apertura,
            maximo=max(valores), minimo=min(valores),     # Yahoo a veces trae máximos por debajo del cierre
            cierre=cierre, volumen=_decimal(fila.get("Volume"), 4) or Decimal("0"),
        )
    return [por_momento[m] for m in sorted(por_momento)]


class YahooCliente:
    NOMBRE = "Yahoo Finance"              # debe coincidir con fuentes_datos.nombre
    TIPOS = frozenset({TipoActivo.ACCION, TipoActivo.ETF, TipoActivo.DIVISA,
                       TipoActivo.INDICE, TipoActivo.BONO})
    PATRON_TICKER = re.compile(r"^[A-Z0-9.^=\-]{1,15}$")
    EJEMPLO_TICKER = "AAPL"
    segundos_entre_cotizaciones = 30
    segundos_entre_velas = 300

    @staticmethod
    def _yf():
        import yfinance   # se importa al usarla: arrastra pandas y retrasaría el arranque de la app
        return yfinance

    @staticmethod
    def _llamar(funcion):
        try:
            return funcion()
        except Exception as error:   # yfinance no tiene una excepción base común
            _log.error("Falló una llamada a Yahoo Finance: %r", error)
            raise ErrorServicioExterno(
                "No se pudo obtener datos de Yahoo Finance. Revisa tu conexión a internet "
                "o inténtalo en unos minutos."
            ) from error

    def existe_simbolo(self, ticker: str) -> bool:
        historial = self._llamar(lambda: self._yf().Ticker(ticker).history(period="5d", interval="1d"))
        return not historial.empty

    def obtener_cotizaciones(self, tickers: Sequence[str]) -> Dict[str, Cotizacion]:
        """Todos los activos en UNA sola descarga (varias peticiones seguidas hacen que Yahoo bloquee)."""
        descarga = self._llamar(lambda: self._yf().download(
            list(tickers), period="5d", interval="1d", group_by="ticker",
            auto_adjust=False, progress=False, threads=True))
        return cotizaciones_desde_descarga(descarga, tickers, datetime.now(timezone.utc))

    def obtener_velas(self, ticker: str, intervalo: IntervaloVela, desde: datetime) -> List[Vela]:
        if intervalo not in _INTERVALOS_YAHOO:
            raise ErrorServicioExterno("Yahoo Finance no entrega velas de %s." % intervalo.value)
        limite = _MAX_DIAS.get(intervalo)
        if limite:
            desde = max(desde, datetime.now(timezone.utc) - timedelta(days=limite))
        historial = self._llamar(lambda: self._yf().Ticker(ticker).history(
            start=desde.astimezone(timezone.utc).strftime("%Y-%m-%d"),
            interval=_INTERVALOS_YAHOO[intervalo], auto_adjust=False, actions=False))
        return velas_desde_historial(historial, intervalo)
