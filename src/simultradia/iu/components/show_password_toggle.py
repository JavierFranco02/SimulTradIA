"""Interruptor «Mostrar contraseña» que controla uno o más PasswordField."""
import tkinter as tk
from typing import Sequence

import ttkbootstrap as ttk

from simultradia.iu.components.password_field import PasswordField


class ShowPasswordToggle(ttk.Checkbutton):
    def __init__(self, parent, campos: Sequence[PasswordField], texto: str = "Mostrar contraseña"):
        variable = tk.BooleanVar(master=parent, value=False)
        super().__init__(parent, text=texto, variable=variable, command=self._alternar,
                         bootstyle="round-toggle")
        self._variable = variable
        self._campos = list(campos)

    def _alternar(self) -> None:
        for campo in self._campos:
            campo.establecer_visible(self._variable.get())
