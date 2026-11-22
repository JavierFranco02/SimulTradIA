"""Pestaña «Proyección»: el abanico de precios posibles (Monte Carlo) y la probabilidad de tocar un nivel.

No es la predicción de la IA: solo muestra qué tan abierto está el rango según la volatilidad reciente.
"""
from decimal import Decimal
from typing import Callable, Optional

import tkinter as tk
import ttkbootstrap as ttk

from simultradia.analisis.montecarlo import Proyeccion
from simultradia.iu.components import ActionButton, FigureView, MetricGrid
from simultradia.iu.formato import precio
from simultradia.iu.ia import textos
from simultradia.iu.ia.graficos import dibujar_proyeccion
from simultradia.iu.styles import ButtonStyle, Fonts, Spacing


class ProyeccionView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=Spacing.MD)
        self._al_calcular: Optional[Callable[[], None]] = None

        barra = ttk.Frame(self)
        barra.pack(fill="x")
        ttk.Label(barra, text="Nivel a vigilar", font=Fonts.BODY).pack(side="left", padx=(0, Spacing.SM))
        self._nivel = tk.StringVar(master=self)
        entrada = ttk.Entry(barra, textvariable=self._nivel, width=14, font=Fonts.BODY)
        entrada.pack(side="left", padx=(0, Spacing.SM))
        entrada.bind("<Return>", lambda _e: self._pulsar_calcular())
        ActionButton(barra, "Calcular", self._pulsar_calcular, estilo=ButtonStyle.LIGHT_OUTLINE).pack(side="left")

        self._mensaje = ttk.Label(self, text="Elige un activo del escáner.", font=Fonts.SUBTITLE)
        self._mensaje.pack(expand=True)
        self._contenido = ttk.Frame(self)
        self._metricas = MetricGrid(self._contenido, columnas=4)
        self._metricas.pack(fill="x", pady=(Spacing.MD, 0))
        self._grafico = FigureView(self._contenido, dibujar_proyeccion)
        self._grafico.pack(fill="both", expand=True)
        ttk.Label(self._contenido, text="Dispersión según la volatilidad reciente: no es la predicción de la IA.",
                  font=Fonts.SMALL).pack(anchor="w", pady=(Spacing.SM, 0))

    def vincular_acciones(self, al_calcular: Callable[[], None]) -> None:
        self._al_calcular = al_calcular

    def texto_nivel(self) -> str:
        return self._nivel.get()

    def limpiar(self, texto: str = "Elige un activo del escáner.") -> None:
        self._contenido.pack_forget()
        self._mensaje.configure(text=texto)
        self._mensaje.pack(expand=True)

    def mostrar(self, proyeccion: Proyeccion, nivel: Optional[float]) -> None:
        self._mensaje.pack_forget()
        self._contenido.pack(fill="both", expand=True)
        mediana = proyeccion.percentiles[50][-1]
        metricas = [
            ("Cierra por encima de hoy", textos.pct(proyeccion.prob_subir)),
            ("Mediana a +%d días" % proyeccion.dias, precio(Decimal(str(round(mediana, 6))))),
            ("Rango 5 – 95 %", "%s – %s" % (precio(Decimal(str(round(proyeccion.percentiles[5][-1], 6)))),
                                            precio(Decimal(str(round(proyeccion.percentiles[95][-1], 6)))))),
        ]
        if proyeccion.prob_tocar_nivel is not None and nivel is not None:
            metricas.append(("Toca %s" % precio(Decimal(str(nivel))), textos.pct(proyeccion.prob_tocar_nivel)))
        self._metricas.establecer(metricas)
        self._grafico.mostrar(proyeccion, nivel)

    def _pulsar_calcular(self) -> None:
        if self._al_calcular:
            self._al_calcular()
