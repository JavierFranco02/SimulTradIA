"""Pestaña «Registro vs. realidad»: el rango que la IA predijo contra el que pasó de verdad (resultado en vivo).

Es distinto de la Evaluación: aquella es la validación histórica al entrenar; esto son predicciones reales ya vencidas.
"""
from typing import Optional

import ttkbootstrap as ttk

from simultradia.domain.entities.prediccion_volatilidad_entity import PrecisionVivo
from simultradia.iu.components import DataTable, FigureView, MetricGrid, Seccion
from simultradia.iu.ia import textos
from simultradia.iu.ia.graficos import dibujar_historial
from simultradia.iu.styles import Fonts, Spacing

_COLUMNAS = (
    ("fecha", "Fecha", 90, "w"),
    ("predicho", "Predicho", 80, "e"),
    ("real", "Real", 80, "e"),
    ("diferencia", "Diferencia", 90, "e"),
    ("niveles", "Nivel (esperado → real)", 170, "w"),
    ("resultado", "Resultado", 90, "w"),
)


class RegistroView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=Spacing.MD)
        self._metricas = MetricGrid(self, columnas=4)
        self._metricas.pack(fill="x")
        self._nota = ttk.Label(self, text="", font=Fonts.SMALL, wraplength=800, justify="left")
        self._nota.pack(anchor="w", pady=(0, Spacing.MD))
        grafico = Seccion(self, "Predicho y real, día a día",
                          "La banda es el intervalo del 80 % que esperaba el modelo. El punto es lo que pasó de verdad.",
                          espaciado=Spacing.MD)
        grafico.pack(fill="x", pady=(0, Spacing.LG))
        self._grafico = FigureView(grafico.cuerpo, dibujar_historial, alto=220)
        self._grafico.pack(fill="x")
        ultimas = Seccion(self, "Últimas predicciones", "", ancho_texto=800)
        ultimas.pack(fill="both", expand=True)
        self._titulo = ultimas.rotulo
        self._tabla = DataTable(ultimas.cuerpo, _COLUMNAS)
        self._tabla.pack(fill="both", expand=True, pady=(Spacing.SM, 0))

    def mostrar_precision(self, precision: PrecisionVivo) -> None:
        def pct_de(valor: Optional[float]) -> str:
            return "—" if valor is None else textos.pct(valor / 100.0, 0)

        self._metricas.establecer([
            ("Predicciones evaluadas", str(precision.evaluadas)),
            ("Nivel acertado", pct_de(precision.porcentaje_nivel)),
            ("Real dentro del intervalo", pct_de(precision.porcentaje_intervalo)),
            ("Error frente a repetir hoy", textos.error_contra_hoy(precision.mejora_hoy)),
        ])
        self._nota.configure(text="" if precision.evaluadas else
                             "Aún no hay predicciones vencidas. Cada día, la IA guarda lo que espera; al día siguiente "
                             "se compara con lo que pasó de verdad y aparece aquí.")

    def mostrar_historial(self, ticker: Optional[str], historial) -> None:
        self._titulo.configure(text=("Últimas predicciones de %s" % ticker) if ticker else "Últimas predicciones")
        self._grafico.mostrar(list(historial))
        self._tabla.establecer_filas([
            (str(p.id_prediccion),
             (textos.fecha(p.generada_en), textos.rango(p.rango_predicho),
              textos.rango(p.rango_real) if p.rango_real is not None else "—",
              textos.diferencia_pp(p), textos.niveles(p), textos.resultado(p)),
             textos.etiqueta_resultado(p))
            for p in historial])
