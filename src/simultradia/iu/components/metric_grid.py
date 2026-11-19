"""Cifras en cuadrícula: el rótulo pequeño arriba y el número debajo, varias por fila.

    grilla = MetricGrid(padre, columnas=4)
    grilla.establecer([("ACIERTO", "54 %"), ("AUC", "0,58"), ("VENTAJA", "+3,1 pp", Colors.SUCCESS)])

Sin recuadros: es la forma de poner varias métricas sin que se solapen (cada una ocupa su columna).
"""
from typing import Optional, Sequence, Tuple, Union

import ttkbootstrap as ttk

from simultradia.iu.styles import Fonts, Spacing

Metrica = Union[Tuple[str, str], Tuple[str, str, Optional[str]]]     # (rótulo, valor[, color])


class MetricGrid(ttk.Frame):
    def __init__(self, parent, columnas: int = 4):
        super().__init__(parent)
        self._columnas = columnas
        for columna in range(columnas):
            self.columnconfigure(columna, weight=1, uniform="metrica")

    def establecer(self, metricas: Sequence[Metrica]) -> None:
        for hijo in self.winfo_children():
            hijo.destroy()
        for posicion, metrica in enumerate(metricas):
            rotulo, valor = metrica[0], metrica[1]
            color = metrica[2] if len(metrica) > 2 else None
            fila, columna = divmod(posicion, self._columnas)
            celda = ttk.Frame(self)
            celda.grid(row=fila, column=columna, sticky="w", padx=(0, Spacing.MD), pady=(0, Spacing.SM))
            ttk.Label(celda, text=rotulo.upper(), font=Fonts.SMALL).pack(anchor="w")
            etiqueta = ttk.Label(celda, text=valor, font=Fonts.VALUE)
            if color:
                etiqueta.configure(bootstyle=color)
            etiqueta.pack(anchor="w")
