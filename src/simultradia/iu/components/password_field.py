"""Campo de contraseña: igual que FormField, pero oculta lo que se escribe."""
import ttkbootstrap as ttk

from simultradia.iu.components.form_field import FormField
from simultradia.iu.styles import Fonts


class PasswordField(FormField):
    CARACTER_OCULTO = "•"

    def _crear_entrada(self, ancho: int):
        return ttk.Entry(self, width=ancho, font=Fonts.BODY, textvariable=self._variable,
                         show=self.CARACTER_OCULTO)

    def establecer_visible(self, visible: bool) -> None:
        self._entrada.configure(show="" if visible else self.CARACTER_OCULTO)
