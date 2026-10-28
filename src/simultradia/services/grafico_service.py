"""Casos de uso del gráfico: velas de un intervalo + indicadores + precio en vivo.

El gráfico no consulta nada: recibe `DatosGrafico` ya calculado. El intervalo no cambia la
cotización: solo cambia qué velas se leen (o se arman agrupando otras, como 4 h y 1 sem).
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from simultradia.analisis.indicadores import bollinger, ema, macd, rsi, sma
from simultradia.analisis.velas import agrupar_velas, aplicar_precio
from simultradia.domain.entities.cotizacion_entity import Cotizacion
from simultradia.domain.entities.vela_entity import Vela
from simultradia.domain.enums import IntervaloVela, TipoActivo
from simultradia.domain.reglas import indicadores as cfg
from simultradia.domain.reglas.intervalos import DERIVADOS, base_de

_VELAS_A_LEER = 500   # velas del intervalo base que se cargan (el tope de lo que se puede mostrar)
Serie = List[Optional[float]]


@dataclass(frozen=True)
class DatosGrafico:
    velas: List[Vela]
    sma: Serie
    ema: Serie
    bb_media: Serie
    bb_superior: Serie
    bb_inferior: Serie
    rsi: Serie
    macd: Serie
    macd_senal: Serie
    macd_hist: Serie


class GraficoService:
    def __init__(self, db, precio_repository):
        self._db = db
        self._precios = precio_repository

    def obtener_datos(self, id_activo: int, intervalo: IntervaloVela) -> DatosGrafico:
        with self._db.obtener_conexion() as conn:
            velas = self._precios.buscar_velas(conn, id_activo, base_de(intervalo), _VELAS_A_LEER)
        if intervalo in DERIVADOS:
            velas = agrupar_velas(velas, intervalo)
        return self._con_indicadores(velas)

    def con_precio(self, datos: DatosGrafico, cotizacion: Cotizacion, intervalo: IntervaloVela,
                   tipo: TipoActivo) -> DatosGrafico:
        """Aplica el precio de ahora a la última vela y recalcula los indicadores.
        Solo la cripto (que no cierra nunca) abre velas nuevas a partir del precio."""
        momento = cotizacion.actualizado_en or datetime.now(timezone.utc)
        velas = aplicar_precio(datos.velas, cotizacion.precio, momento, intervalo,
                               abrir_nuevas=tipo == TipoActivo.CRIPTO)
        return self._con_indicadores(velas)

    @staticmethod
    def _con_indicadores(velas: List[Vela]) -> DatosGrafico:
        cierres = [float(v.cierre) for v in velas]   # float solo para dibujar, nunca para dinero
        media, superior, inferior = bollinger(cierres, cfg.PERIODO_BOLLINGER, cfg.DESVIACIONES_BOLLINGER)
        linea, senal, histograma = macd(cierres, cfg.MACD_RAPIDA, cfg.MACD_LENTA, cfg.MACD_SENAL)
        return DatosGrafico(
            velas=velas, sma=sma(cierres, cfg.PERIODO_SMA), ema=ema(cierres, cfg.PERIODO_EMA),
            bb_media=media, bb_superior=superior, bb_inferior=inferior,
            rsi=rsi(cierres, cfg.PERIODO_RSI), macd=linea, macd_senal=senal, macd_hist=histograma)
