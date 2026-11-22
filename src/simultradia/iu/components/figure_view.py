"""Una figura de matplotlib dentro de la interfaz, para gráficos sencillos que se redibujan con datos nuevos.

    grafico = FigureView(padre, dibujar_proyeccion, alto=220)
    grafico.mostrar(proyeccion, nivel)        # llama dibujar_proyeccion(figura, proyeccion, nivel) y refresca

`dibujar` es una función pura de matplotlib (`dibujar(figura, *datos)`): no sabe de tkinter y se prueba sola.
(El gráfico de velas tiene su propio componente porque además reacciona al mouse.)
"""
from typing import Callable, Optional

import ttkbootstrap as ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from simultradia.iu.styles import Palette


class FigureView(ttk.Frame):
    def __init__(self, parent, dibujar: Callable, alto: Optional[int] = None):
        super().__init__(parent)
        self._dibujar = dibujar
        self._figura = Figure(facecolor=Palette.FONDO)
        self._lienzo = FigureCanvasTkAgg(self._figura, master=self)
        widget = self._lienzo.get_tk_widget()
        widget.configure(background=Palette.FONDO, highlightthickness=0)
        if alto:
            widget.configure(height=alto)
        widget.pack(fill="both", expand=True)

    def mostrar(self, *datos) -> None:
        self._dibujar(self._figura, *datos)
        self._lienzo.draw_idle()
