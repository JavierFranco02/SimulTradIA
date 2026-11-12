"""Base de las ventanas emergentes (modales): centrada sobre la principal, con título y botones.

Cada ventana hija arma su formulario dentro de `self.formulario`, llena `self._campos` (clave del servicio -> campo,
para repartir los errores por campo) y llama a `self._presentar()` al final de su constructor.
Los errores de campo salen bajo su campo; cualquier otro aviso es un diálogo sobre esta misma ventana.
Son vistas pasivas: no llaman a ningún servicio.
"""
import tkinter as tk
from tkinter import messagebox
from typing import Dict

import ttkbootstrap as ttk

from simultradia.iu.components.action_button import ActionButton
from simultradia.iu.components.form_field import FormField
from simultradia.iu.styles import ButtonStyle, Fonts, Spacing


class Dialogo(tk.Toplevel):
    def __init__(self, padre, titulo: str):
        super().__init__(padre)
        self.title(titulo)
        self.resizable(False, False)
        self.transient(padre.winfo_toplevel())
        self.bind("<Escape>", lambda _evento: self.destroy())
        self._campos: Dict[str, FormField] = {}   # clave del servicio -> campo (lo llenan las hijas)

        cuerpo = ttk.Frame(self, padding=Spacing.LG)   # cubre toda la ventana con el fondo del tema
        cuerpo.pack(fill="both", expand=True)
        ttk.Label(cuerpo, text=titulo, font=Fonts.HEADING).pack(anchor="w")
        self.formulario = ttk.Frame(cuerpo)
        self.formulario.pack(fill="x")
        self.botones = ttk.Frame(cuerpo)
        self.botones.pack(fill="x", pady=(Spacing.MD, 0))
        ActionButton(self.botones, "Cancelar", self.destroy, estilo=ButtonStyle.LINK).pack(side="left")

    def _presentar(self) -> None:
        """Se llama al final del constructor de cada hija: centra la ventana y la hace modal."""
        self.update_idletasks()
        ventana = self.master.winfo_toplevel()
        x = ventana.winfo_rootx() + (ventana.winfo_width() - self.winfo_reqwidth()) // 2
        y = ventana.winfo_rooty() + (ventana.winfo_height() - self.winfo_reqheight()) // 3
        self.geometry("+%d+%d" % (max(x, 0), max(y, 0)))
        self.wait_visibility()
        self.grab_set()

    def esta_viva(self) -> bool:
        return bool(self.winfo_exists())

    def mostrar_error(self, texto: str) -> None:
        messagebox.showerror("Error", texto, parent=self)

    def mostrar_errores(self, errores: Dict[str, str]) -> None:
        """Cada mensaje bajo su campo; si no es de un campo de esta ventana, en un diálogo."""
        for clave, texto in errores.items():
            campo = self._campos.get(clave)
            if campo is None:
                self.mostrar_error(texto)
            else:
                campo.mostrar_error(texto)

    def limpiar_errores(self) -> None:
        for campo in self._campos.values():
            campo.ocultar_error()
