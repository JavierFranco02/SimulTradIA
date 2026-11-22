"""Sección: un recuadro con título y, opcionalmente, una línea que explica qué se está viendo.

    seccion = Seccion(padre, "Acierto por periodo", "La prueba se repite en 4 periodos...")
    seccion.pack(fill="x")
    ttk.Label(seccion.cuerpo, text="...").pack()        # lo de dentro va en `cuerpo`
"""
import ttkbootstrap as ttk

from simultradia.iu.components.card import Card
from simultradia.iu.styles import Fonts, Spacing


class Seccion(Card):
    def __init__(self, parent, titulo: str, ayuda: str = "", ancho_texto: int = 900):
        super().__init__(parent)
        ttk.Label(self.cuerpo, text=titulo, font=Fonts.VALUE).pack(anchor="w")
        if ayuda:
            ttk.Label(self.cuerpo, text=ayuda, font=Fonts.SMALL, wraplength=ancho_texto, justify="left").pack(
                anchor="w", pady=(0, Spacing.SM))
        else:
            ttk.Frame(self.cuerpo, height=Spacing.XS).pack()
