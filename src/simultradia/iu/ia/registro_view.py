"""Pestaña «Registro vs. realidad»: lo que la IA predijo contra lo que pasó de verdad (acierto en vivo).

Es distinto de la Evaluación: aquella es la validación histórica al entrenar; esto son predicciones reales ya vencidas.
"""
from typing import Optional

import ttkbootstrap as ttk

from simultradia.domain.entities.prediccion_entity import PrecisionVivo
from simultradia.ia.entrenamiento import Evaluacion
from simultradia.iu.components import DataTable, MetricGrid
from simultradia.iu.ia import textos
from simultradia.iu.styles import Fonts, Spacing

_COLUMNAS = (
    ("fecha", "Fecha", 100, "w"),
    ("prediccion", "Predicción", 100, "w"),
    ("confianza", "Confianza", 90, "e"),
    ("real", "Real", 100, "w"),
    ("resultado", "Resultado", 100, "w"),
)


class RegistroView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=Spacing.MD)
        self._metricas = MetricGrid(self, columnas=4)
        self._metricas.pack(fill="x")
        self._nota = ttk.Label(self, text="", font=Fonts.SMALL)
        self._nota.pack(anchor="w", pady=(0, Spacing.MD))
        self._titulo = ttk.Label(self, text="ÚLTIMAS PREDICCIONES", font=Fonts.SMALL)
        self._titulo.pack(anchor="w")
        self._tabla = DataTable(self, _COLUMNAS)
        self._tabla.pack(fill="both", expand=True)

    def mostrar_precision(self, precision: PrecisionVivo, evaluacion: Optional[Evaluacion]) -> None:
        def pct_de(valor: Optional[float]) -> str:
            return "—" if valor is None else textos.pct(valor / 100.0, 1)

        self._metricas.establecer([
            ("Predicciones evaluadas", str(precision.evaluadas)),
            ("Acierto real", pct_de(precision.porcentaje)),
            ("Últimos 90 días", pct_de(precision.porcentaje_90d)),
            ("Acierto en la validación", textos.pct(evaluacion.acierto, 1) if evaluacion else "—"),
        ])
        self._nota.configure(text="" if precision.evaluadas else
                             "Aún no hay predicciones vencidas: el registro se llena con los días.")

    def mostrar_historial(self, ticker: Optional[str], historial) -> None:
        self._titulo.configure(text=("ÚLTIMAS PREDICCIONES DE %s" % ticker) if ticker else "ÚLTIMAS PREDICCIONES")
        self._tabla.establecer_filas([
            (str(p.id_prediccion),
             (textos.fecha(p.generada_en), textos.direccion(p.direccion), textos.pct(p.confianza),
              textos.direccion(p.direccion_real) if p.direccion_real else "—", textos.resultado(p)),
             textos.etiqueta_resultado(p))
            for p in historial])
