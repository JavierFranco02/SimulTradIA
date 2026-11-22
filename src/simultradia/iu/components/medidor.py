"""Medidor: una barra delgada de 0 a 1 con una marca de referencia opcional.

    medidor = Medidor(padre, marca=1 / 3)         # la marca es, por ejemplo, el azar
    medidor.establecer(0.59, Palette.ALZA)

Es un `tk.Canvas` que se redibuja al cambiar de tamaño.
"""
import tkinter as tk
from typing import Optional

from simultradia.iu.styles import Palette

_ALTO = 14
_GROSOR = 8


class Medidor(tk.Canvas):
    def __init__(self, parent, marca: Optional[float] = None):
        super().__init__(parent, height=_ALTO, background=Palette.FONDO, highlightthickness=0)
        self._marca = marca
        self._valor, self._color = 0.0, Palette.TEXTO
        self.bind("<Configure>", lambda _e: self._dibujar())

    def establecer(self, valor: float, color: str) -> None:
        self._valor, self._color = max(0.0, min(1.0, valor)), color
        self._dibujar()

    def _dibujar(self) -> None:
        self.delete("all")
        ancho = max(self.winfo_width(), 2)
        arriba, abajo = (_ALTO - _GROSOR) / 2, (_ALTO + _GROSOR) / 2
        self.create_rectangle(0, arriba, ancho, abajo, fill=Palette.GRILLA, outline="")
        self.create_rectangle(0, arriba, ancho * self._valor, abajo, fill=self._color, outline="")
        if self._marca is not None:
            x = ancho * self._marca
            self.create_line(x, 0, x, _ALTO, fill=Palette.TEXTO)
