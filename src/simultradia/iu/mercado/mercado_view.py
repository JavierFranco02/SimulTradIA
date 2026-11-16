"""Pantalla Mercado: la lista de activos a la izquierda y el gráfico a la derecha, en un panel dividido.

El borde entre ambos se arrastra con el mouse (splitter). El botón «◀» del encabezado «Activos» oculta la lista
para dejar todo el ancho al gráfico; mientras está oculta queda un riel angosto con «▶» para volver a mostrarla.
Debajo del gráfico va «Operar AAPL» (solo para usuarios que operan): abre la pantalla Operar con el activo elegido.
Esta vista solo organiza el espacio: lo que hay dentro de la lista y del gráfico lo manejan ListaActivosView
y GraficoActivoView (que no saben nada de operar).
"""
from typing import Callable, Optional

import ttkbootstrap as ttk

from simultradia.iu.base.panel_view import PanelView
from simultradia.iu.components import ActionButton
from simultradia.iu.mercado.grafico_view import GraficoActivoView
from simultradia.iu.mercado.lista_view import ListaActivosView
from simultradia.iu.styles import ButtonStyle, Fonts, Spacing

_ANCHO_LISTA = 440       # ancho inicial de la lista
_ANCHO_MINIMO_LISTA = 300
_ANCHO_MINIMO_GRAFICO = 480


class MercadoView(PanelView):
    def __init__(self, parent):
        super().__init__(parent, padding=Spacing.MD)
        self._al_operar: Optional[Callable[[int], None]] = None
        self._id_activo: Optional[int] = None
        ttk.Label(self, text="Mercado", font=Fonts.HEADING).pack(anchor="w", pady=(0, Spacing.SM))

        cuerpo = ttk.Frame(self)
        cuerpo.pack(fill="both", expand=True)
        # Riel con la lista oculta: solo el botón para volver a mostrarla (se empaqueta al ocultar).
        self._riel = ttk.Frame(cuerpo)
        ActionButton(self._riel, "▶", self._alternar_lista, estilo=ButtonStyle.LINK).pack(anchor="n")

        self._panel = ttk.Panedwindow(cuerpo, orient="horizontal")
        self._panel.pack(fill="both", expand=True)

        # Izquierda: encabezado «Activos» con su botón de ocultar, y la lista.
        self._izquierda = ttk.Frame(self._panel)
        encabezado = ttk.Frame(self._izquierda)
        encabezado.pack(fill="x", pady=(0, Spacing.XS))
        ttk.Label(encabezado, text="Activos", font=Fonts.VALUE).pack(side="left")
        ActionButton(encabezado, "◀", self._alternar_lista, estilo=ButtonStyle.LINK).pack(side="right")
        self.lista = ListaActivosView(self._izquierda)
        self.lista.pack(fill="both", expand=True)

        # Derecha: el gráfico y, debajo, la barra con «Operar» (fuera del gráfico: este no sabe de operar).
        self._derecha = ttk.Frame(self._panel)
        self.grafico = GraficoActivoView(self._derecha)
        self.grafico.pack(fill="both", expand=True)
        self._barra_operar = ttk.Frame(self._derecha)       # se muestra al vincular la acción
        ttk.Separator(self._barra_operar).pack(fill="x")
        self._boton_operar = ActionButton(self._barra_operar, "Operar este activo", self._pulsar_operar,
                                          estilo=ButtonStyle.SUCCESS)
        self._boton_operar.pack(side="right", pady=(Spacing.SM, 0))
        self._boton_operar.configure(state="disabled")

        self._panel.add(self._izquierda, weight=1)
        self._panel.add(self._derecha, weight=4)
        self._lista_visible = True
        self._ancho_lista = _ANCHO_LISTA
        self._panel.bind("<ButtonRelease-1>", lambda _evento: self._corregir_ancho())
        self.programar(100, self._fijar_ancho_inicial)

    def vincular_acciones(self, al_operar: Callable[[int], None]) -> None:
        """Activa el botón «Operar»; `al_operar(id_activo)` abre la pantalla de operar."""
        self._al_operar = al_operar
        self._barra_operar.pack(side="bottom", fill="x", before=self.grafico)
        self._boton_operar.configure(state="normal" if self._id_activo is not None else "disabled")

    def establecer_activo_elegido(self, id_activo: int) -> None:
        self._id_activo = id_activo
        ticker = self.lista.ticker_de(id_activo)
        self._boton_operar.establecer_texto("Operar %s" % ticker if ticker else "Operar este activo")
        if self._al_operar:
            self._boton_operar.configure(state="normal")

    def _pulsar_operar(self) -> None:
        if self._al_operar and self._id_activo is not None:
            self._al_operar(self._id_activo)

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
            self._panel.forget(self._izquierda)
            self._riel.pack(side="left", fill="y", padx=(0, Spacing.SM), before=self._panel)
        else:
            self._riel.pack_forget()
            self._panel.insert(0, self._izquierda, weight=1)
            self.programar(20, lambda: self._panel.sashpos(0, self._ancho_lista))
        self._lista_visible = not self._lista_visible
