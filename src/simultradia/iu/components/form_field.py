"""Campo de formulario: etiqueta, caja de texto y, debajo, el mensaje de error del campo.

El mensaje de error está oculto (sin ocupar espacio) hasta que se llama a
mostrar_error(), y vuelve a ocultarse solo cuando el usuario escribe en el campo.
"""
import tkinter as tk
from typing import Callable

import ttkbootstrap as ttk

from simultradia.iu.components.status_message import StatusMessage
from simultradia.iu.styles import Fonts, Spacing


class FormField(ttk.Frame):
    def __init__(self, parent, etiqueta: str, ancho: int = 34):
        super().__init__(parent)
        self._variable = tk.StringVar(master=self)   # guarda lo que hay escrito en la caja
        ttk.Label(self, text=etiqueta, font=Fonts.BODY).pack(anchor="w", pady=(Spacing.SM, 2))
        self._entrada = self._crear_entrada(ancho)
        self._entrada.pack(fill="x")
        self._error = StatusMessage(self, fuente=Fonts.SMALL)
        self._error.pack(fill="x")
        # Cada vez que el texto cambia (el usuario escribe, pega o borra), el error se oculta.
        self._variable.trace_add("write", lambda *_argumentos: self._error.limpiar())

    def _crear_entrada(self, ancho: int):
        """Las clases hijas (como PasswordField) cambian este método para variar la caja."""
        return ttk.Entry(self, width=ancho, font=Fonts.BODY, textvariable=self._variable)

    def obtener(self) -> str:
        return self._variable.get()

    def establecer(self, texto: str) -> None:
        self._variable.set(texto)

    def limpiar(self) -> None:
        self._variable.set("")

    def enfocar(self) -> None:
        self._entrada.focus_set()

    def al_presionar_enter(self, accion: Callable[[], None]) -> None:
        self._entrada.bind("<Return>", lambda _evento: accion())

    def mostrar_error(self, texto: str) -> None:
        self._error.mostrar_error(texto)

    def ocultar_error(self) -> None:
        self._error.limpiar()
