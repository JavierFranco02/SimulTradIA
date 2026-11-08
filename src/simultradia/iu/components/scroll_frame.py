"""Contenedor con barra de desplazamiento vertical: lo que no cabe en el alto se recorre con la rueda del mouse.

    marco = ScrollFrame(padre, ancho=340)
    marco.pack(fill="y")
    ttk.Label(marco.cuerpo, text="...").pack()       # lo de dentro va en `cuerpo`

El contenido ocupa todo el ancho disponible; el alto lo decide lo que se pone dentro.
"""
import tkinter as tk

import ttkbootstrap as ttk

from simultradia.iu.styles import Spacing


class ScrollFrame(ttk.Frame):
    def __init__(self, parent, ancho: int = 340, padding: int = Spacing.SM):
        super().__init__(parent)
        self._lienzo = tk.Canvas(self, width=ancho, highlightthickness=0, borderwidth=0,
                                 background=ttk.Style().lookup("TFrame", "background"))
        barra = ttk.Scrollbar(self, orient="vertical", command=self._lienzo.yview)
        self._lienzo.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self._lienzo.pack(side="left", fill="both", expand=True)
        self.cuerpo = ttk.Frame(self._lienzo, padding=padding)
        self._ventana = self._lienzo.create_window((0, 0), window=self.cuerpo, anchor="nw")
        self.cuerpo.bind("<Configure>", self._al_cambiar_contenido)
        self._lienzo.bind("<Configure>", lambda e: self._lienzo.itemconfigure(self._ventana, width=e.width))
        # La rueda solo actúa mientras el mouse está encima de este marco.
        self.bind("<Enter>", lambda _e: self._lienzo.bind_all("<MouseWheel>", self._rueda))
        self.bind("<Leave>", lambda _e: self._lienzo.unbind_all("<MouseWheel>"))

    def _al_cambiar_contenido(self, _evento) -> None:
        self._lienzo.configure(scrollregion=self._lienzo.bbox("all"))
        # Si todo cabe, la barra no tiene nada que recorrer: se deja el contenido arriba.
        if self.cuerpo.winfo_reqheight() <= self._lienzo.winfo_height():
            self._lienzo.yview_moveto(0)

    def _rueda(self, evento) -> None:
        if self.cuerpo.winfo_reqheight() > self._lienzo.winfo_height():
            self._lienzo.yview_scroll(int(-evento.delta / 120), "units")
