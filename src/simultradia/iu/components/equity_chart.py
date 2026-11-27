"""Gráfico de la curva de capital para la interfaz: pone la figura de matplotlib dentro de tkinter.

    grafico = EquityChart(padre, horas=24)                         # rango inicial: las últimas 24 horas
    grafico = EquityChart(padre, mensaje_vacio="Aún no hay historial.")     # o con un mensaje propio para «sin curva»
    grafico.establecer_datos(puntos, caidas, capital_inicial)      # lo que entrega PortafolioService
    grafico.establecer_rango(168)                                  # solo las últimas 168 horas (None = todo)
    grafico.establecer_mensaje_vacio("Sin datos todavía.")         # cambia lo que se ve cuando no hay curva

`mensaje_vacio` es lo que se escribe en el lugar del gráfico cuando hay menos de 2 puntos. Por omisión es un texto
genérico («No hay puntos suficientes.»); cada pantalla puede poner uno que explique por qué falta la curva.

Al pasar el mouse sobre la curva, arriba a la izquierda se leen la fecha y hora del punto y su patrimonio, saldo y
posiciones. Cada actualización redibuja todo: con unos miles de puntos es rápido.
"""
from decimal import Decimal
from typing import Optional, Sequence

import ttkbootstrap as ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from simultradia.domain.entities.snapshot_entity import SnapshotPortafolio
from simultradia.iu.components.equity_render import MENSAJE_SIN_PUNTOS, Dibujo, dibujar_curva, texto_de_punto
from simultradia.iu.styles import Palette


class EquityChart(ttk.Frame):
    def __init__(self, parent, horas: Optional[int] = None, mensaje_vacio: str = MENSAJE_SIN_PUNTOS):
        super().__init__(parent)
        self._mensaje_vacio = mensaje_vacio
        self._figura = Figure(facecolor=Palette.FONDO)
        self._lienzo = FigureCanvasTkAgg(self._figura, master=self)
        widget = self._lienzo.get_tk_widget()
        widget.configure(background=Palette.FONDO, highlightthickness=0)
        widget.pack(fill="both", expand=True)

        self._puntos: Optional[Sequence[SnapshotPortafolio]] = None
        self._caidas: Sequence[float] = ()
        self._capital = Decimal(0)
        self._horas: Optional[int] = horas       # cuántas horas se ven (None = toda la historia)
        self._dibujo: Optional[Dibujo] = None
        self._indice_texto = None
        self._lienzo.mpl_connect("motion_notify_event", self._al_mover)

    def establecer_datos(self, puntos: Sequence[SnapshotPortafolio], caidas: Sequence[float],
                         capital_inicial: Decimal) -> None:
        self._puntos, self._caidas, self._capital = puntos, caidas, capital_inicial
        self._redibujar()

    def establecer_rango(self, horas: Optional[int]) -> None:
        """Muestra solo las últimas `horas` horas (None = toda la historia)."""
        self._horas = horas
        self._redibujar()

    def establecer_mensaje_vacio(self, mensaje: str) -> None:
        """Cambia el texto que se ve cuando no hay curva (y lo redibuja si ya se mostraba)."""
        self._mensaje_vacio = mensaje
        if self._puntos is not None:
            self._redibujar()

    def limpiar(self) -> None:
        self._puntos, self._dibujo = None, None
        self._figura.clear()
        self._lienzo.draw_idle()

    def _redibujar(self) -> None:
        self._dibujo = dibujar_curva(self._figura, self._puntos, self._caidas, self._capital, self._horas,
                                     self._mensaje_vacio)
        self._indice_texto = None
        self._lienzo.draw_idle()

    def _al_mover(self, evento) -> None:
        dibujo = self._dibujo
        if dibujo is None or evento.inaxes is not dibujo.ejes or evento.xdata is None:
            return
        indice = min(range(len(dibujo.xs)), key=lambda i: abs(dibujo.xs[i] - evento.xdata))
        if indice != self._indice_texto:
            self._indice_texto = indice
            dibujo.texto.set_text(texto_de_punto(dibujo.puntos[indice]))
            self._lienzo.draw_idle()
