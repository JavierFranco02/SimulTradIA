"""Sección de bienvenida del panel. PROVISIONAL: luego se reemplaza por el resumen del panel."""
import ttkbootstrap as ttk

from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.iu.styles import Fonts, Spacing


class InicioView(ttk.Frame):
    def __init__(self, parent, usuario: Usuario):
        super().__init__(parent, padding=Spacing.LG)
        centro = ttk.Frame(self)
        centro.pack(expand=True)

        ttk.Label(centro, text="¡Hola, %s!" % usuario.nombre, font=Fonts.HEADING).pack()
        ttk.Label(
            centro,
            text="El login funciona.\nAquí irá el resumen del panel.",
            font=Fonts.BODY,
            justify="center",
        ).pack(pady=(Spacing.MD, 0))
