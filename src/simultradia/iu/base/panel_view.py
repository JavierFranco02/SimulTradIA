"""Base de las pantallas de sección (Mercado, ficha, administración...).

Reúne lo que todas comparten: título con subtítulo, avisos al usuario (error o éxito) como
diálogos, saber si la pantalla sigue viva y programar tareas repetidas que se cancelan solas al
salir. Cada pantalla hija solo dibuja SU contenido.

Los avisos son diálogos y no texto fijo en la pantalla: un "guardado" o un error no debe quedarse
escrito ahí cuando ya no importa.
"""
from tkinter import messagebox
from typing import Callable, List, Optional

import ttkbootstrap as ttk

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

    def establecer_subtitulo(self, texto: str) -> None:
        self._subtitulo.configure(text=texto)

    def _padre_aviso(self):
        """Ventana sobre la que se abre el diálogo (las hijas con ventanas emergentes la cambian)."""
        return self

    def mostrar_error(self, texto: str) -> None:
        messagebox.showerror("Error", texto, parent=self._padre_aviso())

    def mostrar_exito(self, texto: str) -> None:
        messagebox.showinfo("Listo", texto, parent=self._padre_aviso())

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
