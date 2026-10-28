"""Lista desplegable con etiqueta (como FormField, pero para elegir entre opciones fijas).

    campo = SelectField(padre, "Tipo", [("cripto", "Cripto"), ("accion", "Acción")])
    campo.obtener()      # -> "cripto" (la clave de la opción elegida, no su texto)

Sin etiqueta (`etiqueta=None`) es solo la lista, para usarla dentro de una barra de herramientas.
"""
from typing import Callable, Optional, Sequence, Tuple

import tkinter as tk
import ttkbootstrap as ttk

from simultradia.iu.styles import Fonts, Spacing

Opcion = Tuple[str, str]   # (clave, texto que se ve)


class SelectField(ttk.Frame):
    def __init__(self, parent, etiqueta: Optional[str], opciones: Sequence[Opcion] = (), ancho: int = 20):
        super().__init__(parent)
        self._claves = []
        self._texto = tk.StringVar(master=self)
        if etiqueta:
            ttk.Label(self, text=etiqueta, font=Fonts.BODY).pack(anchor="w", pady=(Spacing.SM, 2))
        self._lista = ttk.Combobox(self, textvariable=self._texto, state="readonly", width=ancho,
                                   font=Fonts.BODY)
        self._lista.pack(fill="x")
        self.establecer_opciones(opciones)

    def establecer_opciones(self, opciones: Sequence[Opcion], elegida: Optional[str] = None) -> None:
        """Cambia las opciones. Si `elegida` no se indica, se conserva la que estaba (si sigue existiendo)."""
        anterior = self.obtener() if elegida is None else elegida
        self._claves = [clave for clave, _texto in opciones]
        self._lista.configure(values=[texto for _clave, texto in opciones])
        if anterior in self._claves:
            self.establecer(anterior)
        elif self._claves:
            self.establecer(self._claves[0])
        else:
            self._texto.set("")

    def obtener(self) -> Optional[str]:
        indice = self._lista.current()
        return self._claves[indice] if 0 <= indice < len(self._claves) else None

    def establecer(self, clave: str) -> None:
        self._lista.current(self._claves.index(clave))

    def al_cambiar(self, accion: Callable[[], None]) -> None:
        self._lista.bind("<<ComboboxSelected>>", lambda _evento: accion())
