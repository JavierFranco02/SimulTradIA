"""Pestaña «Registro vs. realidad»: el rango que la IA predijo contra el que pasó de verdad (resultado en vivo).

Es distinto de la Evaluación: aquella es la validación histórica al entrenar; esto son predicciones reales ya vencidas.
"""
from typing import Optional

import ttkbootstrap as ttk

from simultradia.domain.entities.prediccion_volatilidad_entity import PrecisionVivo
from simultradia.ia.volatilidad import Evaluacion
from simultradia.iu.components import DataTable, FigureView, MetricGrid
from simultradia.iu.ia import textos
from simultradia.iu.ia.graficos import dibujar_historial
from simultradia.iu.styles import Fonts, Spacing

_COLUMNAS = (
    ("fecha", "Fecha", 90, "w"),
    ("predicho", "Predicho", 90, "e"),
    ("nivel", "Nivel", 80, "w"),
    ("real", "Real", 90, "e"),
    ("nivel_real", "Nivel real", 90, "w"),
    ("resultado", "Nivel", 90, "w"),
)


class RegistroView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=Spacing.MD)
        self._metricas = MetricGrid(self, columnas=4)
        self._metricas.pack(fill="x")
        self._nota = ttk.Label(self, text="", font=Fonts.SMALL)
        self._nota.pack(anchor="w", pady=(0, Spacing.SM))
        self._grafico = FigureView(self, dibujar_historial, alto=200)
        self._grafico.pack(fill="x")
        self._titulo = ttk.Label(self, text="ÚLTIMAS PREDICCIONES", font=Fonts.SMALL)
        self._titulo.pack(anchor="w", pady=(Spacing.SM, 0))
        self._tabla = DataTable(self, _COLUMNAS)
        self._tabla.pack(fill="both", expand=True)

    def mostrar_precision(self, precision: PrecisionVivo, evaluacion: Optional[Evaluacion]) -> None:
        def pct_de(valor: Optional[float]) -> str:
            return "—" if valor is None else textos.pct(valor / 100.0, 0)

        error = textos.error_pct(precision.error_modelo) if precision.error_modelo is not None else "—"
        error_hoy = textos.error_pct(precision.error_hoy) if precision.error_hoy is not None else "—"
        self._metricas.establecer([
            ("Predicciones evaluadas", str(precision.evaluadas)),
            ("Nivel acertado", pct_de(precision.porcentaje_nivel)),
            ("Real dentro del intervalo", pct_de(precision.porcentaje_intervalo)),
            ("Mejora frente a repetir hoy", textos.pct(precision.mejora_hoy, 0) if precision.mejora_hoy is not None else "—"),
            ("Error del modelo (90 d.)", error),
            ("Error repitiendo hoy (90 d.)", error_hoy),
            ("Error en la validación", textos.error_pct(evaluacion.error) if evaluacion else "—"),
        ])
        self._nota.configure(text="" if precision.evaluadas else
                             "Aún no hay predicciones vencidas: el registro se llena con los días.")

    def mostrar_historial(self, ticker: Optional[str], historial) -> None:
        self._titulo.configure(text=("ÚLTIMAS PREDICCIONES DE %s" % ticker) if ticker else "ÚLTIMAS PREDICCIONES")
        self._grafico.mostrar(list(historial))
        self._tabla.establecer_filas([
            (str(p.id_prediccion),
             (textos.fecha(p.generada_en), textos.rango(p.rango_predicho), textos.nivel(p.nivel),
              textos.rango(p.rango_real) if p.rango_real is not None else "—",
              textos.nivel(p.nivel_real) if p.nivel_real else "—", textos.resultado(p)),
             textos.etiqueta_resultado(p))
            for p in historial])
