"""Lista de barras horizontales: «texto  ▇▇▇▇▁▁  valor». Sirve para probabilidades, factores e importancias.

    barras = BarList(padre)                       # de 0 a 1, rellenando desde la izquierda
    barras.establecer([("Alcista", 0.54, Palette.ALZA, "54 %")])
    factores = BarList(padre, centrada=True)      # de -1 a 1, desde el centro (rojo a la izquierda, verde a la derecha)

Cada barra es un `tk.Canvas` pequeño que se redibuja al cambiar de tamaño.
"""
import tkinter as tk
from typing import Sequence, Tuple

import ttkbootstrap as ttk

from simultradia.iu.styles import Fonts, Palette, Spacing

Barra = Tuple[str, float, str, str]       # (texto, valor, color de la barra, texto del valor)
_ALTO = 14
_GROSOR = 6


class BarList(ttk.Frame):
    def __init__(self, parent, centrada: bool = False, ancho_texto: int = 22, ancho_valor: int = 7):
        super().__init__(parent)
        self._centrada = centrada
        self._ancho_texto, self._ancho_valor = ancho_texto, ancho_valor
        self.columnconfigure(1, weight=1)

    def establecer(self, barras: Sequence[Barra]) -> None:
        for hijo in self.winfo_children():
            hijo.destroy()
        for fila, (texto, valor, color, texto_valor) in enumerate(barras):
            ttk.Label(self, text=texto, font=Fonts.BODY, width=self._ancho_texto).grid(
                row=fila, column=0, sticky="w", pady=2)
            lienzo = tk.Canvas(self, height=_ALTO, background=Palette.FONDO, highlightthickness=0)
            lienzo.grid(row=fila, column=1, sticky="ew", padx=Spacing.SM, pady=2)
            lienzo.bind("<Configure>", lambda _e, c=lienzo, v=valor, col=color: self._dibujar(c, v, col))
            ttk.Label(self, text=texto_valor, font=Fonts.BODY, width=self._ancho_valor, anchor="e").grid(
                row=fila, column=2, sticky="e", pady=2)

    def _dibujar(self, lienzo, valor: float, color: str) -> None:
        lienzo.delete("all")
        ancho = max(lienzo.winfo_width(), 2)
        arriba, abajo = (_ALTO - _GROSOR) / 2, (_ALTO + _GROSOR) / 2
        lienzo.create_rectangle(0, arriba, ancho, abajo, fill=Palette.GRILLA, outline="")
        if self._centrada:
            mitad = ancho / 2
            extremo = mitad + max(-1.0, min(1.0, valor)) * mitad
            lienzo.create_rectangle(min(mitad, extremo), arriba, max(mitad, extremo), abajo,
                                    fill=color, outline="")
            lienzo.create_line(mitad, 0, mitad, _ALTO, fill=Palette.TEXTO)
        else:
            lienzo.create_rectangle(0, arriba, ancho * max(0.0, min(1.0, valor)), abajo,
                                    fill=color, outline="")
