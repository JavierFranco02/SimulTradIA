"""Gráfico de velas para la interfaz: pone la figura de matplotlib dentro de tkinter.

    grafico = CandleChart(padre)
    grafico.establecer_datos(datos, IntervaloVela.H1)             # datos = DatosGrafico
    grafico.establecer_opciones(OpcionesGrafico(visibles=60, rsi=True))

Al pasar el mouse sobre una vela, arriba a la izquierda se leen su apertura, máximo, mínimo,
cierre y volumen. Cada actualización redibuja todo: con unos cientos de velas es rápido.
"""
import ttkbootstrap as ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from simultradia.domain.enums import IntervaloVela
from simultradia.iu.components.candle_render import (
    Dibujo, OpcionesGrafico, dibujar_velas, texto_de_vela)
from simultradia.iu.styles import Palette


class CandleChart(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._figura = Figure(facecolor=Palette.FONDO)
        self._lienzo = FigureCanvasTkAgg(self._figura, master=self)
        widget = self._lienzo.get_tk_widget()
        widget.configure(background=Palette.FONDO, highlightthickness=0)
        widget.pack(fill="both", expand=True)

        self._datos = None
        self._intervalo = IntervaloVela.H1
        self._opciones = OpcionesGrafico()
        self._dibujo = None
        self._indice_texto = None
        self._lienzo.mpl_connect("motion_notify_event", self._al_mover)

    def establecer_datos(self, datos, intervalo: IntervaloVela) -> None:
        self._datos, self._intervalo = datos, intervalo
        self._redibujar()

    def establecer_opciones(self, opciones: OpcionesGrafico) -> None:
        self._opciones = opciones
        self._redibujar()

    def limpiar(self) -> None:
        """Deja el lienzo vacío (mientras llegan los datos de otro activo)."""
        self._datos, self._dibujo = None, None
        self._figura.clear()
        self._lienzo.draw_idle()

    def _redibujar(self) -> None:
        self._dibujo = dibujar_velas(self._figura, self._datos, self._intervalo, self._opciones)
        self._indice_texto = None
        self._lienzo.draw_idle()

    def _al_mover(self, evento) -> None:
        dibujo: Dibujo = self._dibujo
        if dibujo is None or evento.inaxes is not dibujo.ejes or evento.xdata is None:
            return
        indice = int(round(evento.xdata))
        if 0 <= indice < len(dibujo.velas) and indice != self._indice_texto:
            self._indice_texto = indice
            dibujo.texto.set_text(texto_de_vela(dibujo.velas[indice]))
            self._lienzo.draw_idle()
