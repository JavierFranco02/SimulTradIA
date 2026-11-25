"""Sección: un recuadro con título y, opcionalmente, una línea que explica qué se está viendo.

    seccion = Seccion(padre, "Acierto por periodo", "La prueba se repite en 4 periodos...")
    seccion.pack(fill="x")
    ttk.Label(seccion.cuerpo, text="...").pack()        # lo de dentro va en `cuerpo`

`espaciado` es el espacio que queda debajo de la descripción.
"""
import ttkbootstrap as ttk

from simultradia.iu.components.card import Card
from simultradia.iu.styles import Fonts, Spacing


class Seccion(Card):
    def __init__(self, parent, titulo: str, ayuda: str = "", ancho_texto: int = 900, espaciado: int = Spacing.SM):
        super().__init__(parent)
        self.rotulo = ttk.Label(self.cuerpo, text=titulo, font=Fonts.VALUE)       # se puede cambiar con configure
        self.rotulo.pack(anchor="w")
        if ayuda:
            ttk.Label(self.cuerpo, text=ayuda, font=Fonts.SMALL, wraplength=ancho_texto, justify="left").pack(
                anchor="w", pady=(0, espaciado))
        else:
            ttk.Frame(self.cuerpo, height=Spacing.XS).pack()
