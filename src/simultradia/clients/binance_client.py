"""Adaptador a Binance (con la librería ccxt): SOLO trae datos de afuera.

No escribe en la base ni decide nada: devuelve entidades y los servicios hacen el resto.
Los pares se escriben como los entiende Binance: "BTC/USDT". Se usa la API pública,
sin cuenta ni claves.
"""
import logging
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Sequence

import ccxt

from simultradia.core.exceptions import ErrorServicioExterno
from simultradia.domain.entities.cotizacion_entity import Cotizacion
from simultradia.domain.entities.vela_entity import Vela
from simultradia.domain.enums import IntervaloVela, TipoActivo

_log = logging.getLogger(__name__)
_VELAS_POR_LLAMADA = 1000   # máximo que entrega Binance en una sola petición


def _decimal(valor) -> Optional[Decimal]:
    return None if valor is None else Decimal(str(valor))


class BinanceCliente:
    # Lo que la ingesta y la administración necesitan saber de CUALQUIER fuente de datos:
    NOMBRE = "Binance"                    # debe coincidir con fuentes_datos.nombre
    TIPOS = frozenset({TipoActivo.CRIPTO})
    PATRON_TICKER = re.compile(r"^[A-Z0-9]{2,15}/USDT$")
    EJEMPLO_TICKER = "BTC/USDT"
    segundos_entre_cotizaciones = 2       # cada cuánto conviene pedirle precios
    segundos_entre_velas = 60

    def __init__(self):
        self._exchange = None   # se crea al primer uso: abrir la app no debe depender de internet

    def _api(self):
        if self._exchange is None:
            self._exchange = ccxt.binance({"enableRateLimit": True})
        return self._exchange

    @staticmethod
    def _llamar(funcion):
        try:
            return funcion()
        except ccxt.BaseError as error:
            _log.error("Falló una llamada a Binance: %r", error)
            raise ErrorServicioExterno(
                "No se pudo obtener datos de Binance. Revisa tu conexión a internet."
            ) from error

    def existe_simbolo(self, ticker: str) -> bool:
        """True si Binance tiene ese par de spot activo."""
        self._llamar(lambda: self._api().load_markets())
        mercado = self._api().markets.get(ticker)
        return bool(mercado and mercado.get("spot") and mercado.get("active", True))

    def obtener_cotizaciones(self, tickers: Sequence[str]) -> Dict[str, Cotizacion]:
        """Precio actual y datos de las últimas 24 h de cada par, en UNA sola petición.
        Los pares que Binance no devuelva simplemente no aparecen en el resultado."""
        brutas = self._llamar(lambda: self._api().fetch_tickers(list(tickers)))
        ahora = datetime.now(timezone.utc)
        resultado: Dict[str, Cotizacion] = {}
        for ticker, dato in brutas.items():
            if ticker not in tickers or dato.get("last") is None:
                continue
            resultado[ticker] = Cotizacion(
                precio=_decimal(dato["last"]),
                cierre_anterior=_decimal(dato.get("open")),
                variacion_pct_dia=_decimal(dato.get("percentage")),
                maximo_dia=_decimal(dato.get("high")),
                minimo_dia=_decimal(dato.get("low")),
                volumen_dia=_decimal(dato.get("quoteVolume")),   # en USDT: comparable entre activos
                actualizado_en=ahora,
            )
        return resultado

    def obtener_velas(self, ticker: str, intervalo: IntervaloVela, desde: datetime) -> List[Vela]:
        """Velas de `intervalo` desde `desde` hasta ahora (pide en tandas de 1000)."""
        api = self._api()
        inicio_ms = int(desde.timestamp() * 1000)
        filas: list = []
        while True:
            tanda = self._llamar(lambda: api.fetch_ohlcv(
                ticker, intervalo.value, since=inicio_ms, limit=_VELAS_POR_LLAMADA))
            if not tanda:
                break
            filas.extend(tanda)
            if len(tanda) < _VELAS_POR_LLAMADA:
                break
            inicio_ms = tanda[-1][0] + 1
        return [
            Vela(
                momento=datetime.fromtimestamp(f[0] / 1000, tz=timezone.utc),
                apertura=Decimal(str(f[1])), maximo=Decimal(str(f[2])),
                minimo=Decimal(str(f[3])), cierre=Decimal(str(f[4])),
                volumen=Decimal(str(f[5] or 0)),
            )
            for f in filas
        ]
