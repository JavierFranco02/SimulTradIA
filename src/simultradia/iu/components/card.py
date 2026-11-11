"""Tarjeta: un recuadro con borde de 1 px para agrupar datos relacionados.

    tarjeta = Card(padre)
    tarjeta.pack(fill="x")
    ttk.Label(tarjeta.cuerpo, text="Saldo").pack()      # lo de dentro va en `cuerpo`

Misma idea que la tarjeta de los formularios (FormView): borde con el color apagado del tema.
"""
import ttkbootstrap as ttk

from simultradia.iu.styles import Colors, Spacing


class Card(ttk.Frame):
    def __init__(self, parent, padding: int = Spacing.MD):
        super().__init__(parent, padding=1, bootstyle=Colors.MUTED)   # el borde
        self.cuerpo = ttk.Frame(self, padding=padding)
        self.cuerpo.pack(fill="both", expand=True)
