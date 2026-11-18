"""Gráfico de la curva de capital para la interfaz: pone la figura de matplotlib dentro de tkinter.

    grafico = EquityChart(padre)
    grafico.establecer_datos(puntos, caidas, capital_inicial)      # lo que entrega PortafolioService
    grafico.establecer_rango(168)                                  # solo las últimas 168 horas (None = todo)

Al pasar el mouse sobre la curva, arriba a la izquierda se leen la fecha y hora del punto y su patrimonio, saldo y
posiciones. Cada actualización redibuja todo: con unos miles de puntos es rápido.
"""
from decimal import Decimal
from typing import Optional, Sequence

import ttkbootstrap as ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from simultradia.domain.entities.snapshot_entity import SnapshotPortafolio
from simultradia.iu.components.equity_render import Dibujo, dibujar_curva, texto_de_punto
from simultradia.iu.styles import Palette


class EquityChart(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._figura = Figure(facecolor=Palette.FONDO)
        self._lienzo = FigureCanvasTkAgg(self._figura, master=self)
        widget = self._lienzo.get_tk_widget()
        widget.configure(background=Palette.FONDO, highlightthickness=0)
        widget.pack(fill="both", expand=True)

        self._puntos: Optional[Sequence[SnapshotPortafolio]] = None
        self._caidas: Sequence[float] = ()
        self._capital = Decimal(0)
        self._horas: Optional[int] = None
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

    def limpiar(self) -> None:
        self._puntos, self._dibujo = None, None
        self._figura.clear()
        self._lienzo.draw_idle()

    def _redibujar(self) -> None:
        self._dibujo = dibujar_curva(self._figura, self._puntos, self._caidas, self._capital, self._horas)
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
