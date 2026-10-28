"""Pantalla Mercado: la lista de activos a la izquierda y el gráfico a la derecha, en un panel dividido.

El borde entre ambos se arrastra con el mouse (splitter). El botón de arriba oculta o muestra
la lista para dejar todo el ancho al gráfico. Esta vista solo organiza el espacio: lo que hay
dentro de cada lado lo manejan ListaActivosView y GraficoActivoView.
"""
import ttkbootstrap as ttk

from simultradia.iu.base.panel_view import PanelView
from simultradia.iu.mercado.grafico_view import GraficoActivoView
from simultradia.iu.mercado.lista_view import ListaActivosView
from simultradia.iu.styles import ButtonStyle, Fonts, Spacing
from simultradia.iu.components import ActionButton

_ANCHO_LISTA = 360       # ancho inicial de la lista
_ANCHO_MINIMO_LISTA = 240
_ANCHO_MINIMO_GRAFICO = 480


class MercadoView(PanelView):
    def __init__(self, parent):
        super().__init__(parent, padding=Spacing.MD)
        cabecera = ttk.Frame(self)
        cabecera.pack(fill="x", pady=(0, Spacing.SM), before=self._mensaje)
        ttk.Label(cabecera, text="Mercado", font=Fonts.HEADING).pack(side="left")
        self._boton_lista = ActionButton(cabecera, "◀ Ocultar lista", self._alternar_lista,
                                         estilo=ButtonStyle.LINK)
        self._boton_lista.pack(side="right")

        # self._panel = ttk.PanedWindow(self, orient="horizontal") # Nombre en tkinter
        self._panel = ttk.Panedwindow(self, orient="horizontal") # Nombre en ttkboostrap
        self._panel.pack(fill="both", expand=True)
        self.lista = ListaActivosView(self._panel)
        self.grafico = GraficoActivoView(self._panel)
        self._panel.add(self.lista, weight=1)
        self._panel.add(self.grafico, weight=4)
        self._lista_visible = True
        self._ancho_lista = _ANCHO_LISTA
        self._panel.bind("<ButtonRelease-1>", lambda _evento: self._corregir_ancho())
        self.programar(100, self._fijar_ancho_inicial)

    def _fijar_ancho_inicial(self) -> None:
        try:
            self._panel.sashpos(0, _ANCHO_LISTA)
        except Exception:   # la ventana aún no tiene tamaño; el reparto por pesos queda igual
            pass

    def _corregir_ancho(self) -> None:
        """Al soltar el borde, evita que la lista o el gráfico queden tan chicos que no sirvan."""
        if not self._lista_visible:
            return
        total = self._panel.winfo_width()
        posicion = self._panel.sashpos(0)
        corregida = max(_ANCHO_MINIMO_LISTA, min(posicion, total - _ANCHO_MINIMO_GRAFICO))
        if corregida != posicion:
            self._panel.sashpos(0, corregida)

    def _alternar_lista(self) -> None:
        if self._lista_visible:
            self._ancho_lista = self._panel.sashpos(0)     # se recuerda para volver al mismo ancho
            self._panel.forget(self.lista)
            self._boton_lista.configure(text="▶ Mostrar lista")
        else:
            self._panel.insert(0, self.lista, weight=1)
            self.programar(20, lambda: self._panel.sashpos(0, self._ancho_lista))
            self._boton_lista.configure(text="◀ Ocultar lista")
        self._lista_visible = not self._lista_visible
