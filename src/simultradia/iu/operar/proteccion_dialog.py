"""Ventana emergente de Operar: poner, cambiar o quitar el stop-loss y el take-profit de una posición.

Vista pasiva: OperarView la abre y le reenvía los errores y mensajes que ordena el controlador.
"""
from typing import Callable

import ttkbootstrap as ttk

from simultradia.iu.components import ActionButton, Dialogo, FormField
from simultradia.iu.styles import Colors, Fonts, Spacing


class EditarProteccionDialog(Dialogo):
    def __init__(self, padre, id_activo: int, ticker: str, stop_loss: str, take_profit: str,
                 al_guardar: Callable[[int, str, str], None]):
        super().__init__(padre, "Stop-loss y take-profit · %s" % ticker)
        ttk.Label(self.formulario, font=Fonts.SMALL, bootstyle=Colors.MUTED, justify="left", wraplength=380,
                  text="Déjalo vacío para quitar ese nivel. El stop-loss debe quedar por debajo del precio actual "
                       "y el take-profit por encima. Cuando el precio llegue a uno, se vende toda la posición."
                  ).pack(anchor="w", pady=(Spacing.SM, 0))
        self._stop_loss = FormField(self.formulario, "Stop-loss (vende si el precio cae hasta aquí)", ancho=40)
        self._take_profit = FormField(self.formulario, "Take-profit (vende si el precio sube hasta aquí)", ancho=40)
        self._stop_loss.pack(fill="x")
        self._take_profit.pack(fill="x")
        self._stop_loss.establecer(stop_loss)
        self._take_profit.establecer(take_profit)
        self._campos = {"stop_loss": self._stop_loss, "take_profit": self._take_profit}

        def guardar() -> None:
            al_guardar(id_activo, self._stop_loss.obtener(), self._take_profit.obtener())

        ActionButton(self.botones, "Guardar", guardar).pack(side="right")
        self._take_profit.al_presionar_enter(guardar)
        self._stop_loss.enfocar()
        self._presentar()
