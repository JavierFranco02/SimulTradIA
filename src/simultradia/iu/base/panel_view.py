"""Base de las pantallas de sección (Mercado, ficha, administración...).

Reúne lo que todas comparten: título con subtítulo, el mensaje general (error o éxito),
saber si la pantalla sigue viva y programar tareas repetidas que se cancelan solas al salir.
Cada pantalla hija solo dibuja SU contenido.
"""
from typing import Callable, List, Optional

import ttkbootstrap as ttk

from simultradia.iu.components import StatusMessage
from simultradia.iu.styles import Colors, Fonts, Spacing


class PanelView(ttk.Frame):
    def __init__(self, parent, titulo: Optional[str] = None, subtitulo: str = "",
                 padding: int = Spacing.LG):
        super().__init__(parent, padding=padding)
        self._tareas: List[str] = []
        if titulo:
            ttk.Label(self, text=titulo, font=Fonts.TITLE).pack(anchor="w")
            self._subtitulo = ttk.Label(self, text=subtitulo, font=Fonts.SUBTITLE, bootstyle=Colors.MUTED)
            self._subtitulo.pack(anchor="w", pady=(2, Spacing.MD))
        self._mensaje = StatusMessage(self)
        self._mensaje.pack(fill="x")

    def establecer_subtitulo(self, texto: str) -> None:
        self._subtitulo.configure(text=texto)

    def mostrar_error(self, texto: str) -> None:
        self._mensaje.mostrar_error(texto)

    def mostrar_exito(self, texto: str) -> None:
        self._mensaje.mostrar_exito(texto)

    def limpiar_mensaje(self) -> None:
        self._mensaje.limpiar()

    def esta_viva(self) -> bool:
        """False si el usuario ya cambió de sección y esta vista fue destruida."""
        return bool(self.winfo_exists())

    def programar(self, milisegundos: int, accion: Callable[[], None]) -> None:
        """Ejecuta `accion` dentro de `milisegundos`. Si la pantalla se cierra antes, se cancela."""
        self._tareas.append(self.after(milisegundos, accion))

    def destroy(self) -> None:
        for tarea in self._tareas:
            try:
                self.after_cancel(tarea)
            except Exception:   # ya se había ejecutado
                pass
        super().destroy()
