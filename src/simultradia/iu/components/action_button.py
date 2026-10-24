"""Botón que puede quedar «ocupado» (desactivado y con otro texto) mientras algo se procesa."""
import ttkbootstrap as ttk

from simultradia.iu.styles import ButtonStyle


class ActionButton(ttk.Button):
    def __init__(self, parent, texto: str, comando, texto_ocupado: str = "Procesando...",
                 estilo: str = ButtonStyle.PRIMARY):
        super().__init__(parent, text=texto, command=comando, bootstyle=estilo)
        self._texto = texto
        self._texto_ocupado = texto_ocupado

    @property
    def ocupado(self) -> bool:
        return str(self.cget("state")) == "disabled"

    def establecer_ocupado(self, ocupado: bool) -> None:
        self.configure(
            state="disabled" if ocupado else "normal",
            text=self._texto_ocupado if ocupado else self._texto,
        )
