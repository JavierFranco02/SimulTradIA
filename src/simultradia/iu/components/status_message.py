"""Mensaje para el usuario (error o confirmación).

Mientras no hay texto NO ocupa espacio: la etiqueta se quita de la pantalla
(pack_forget) y solo se vuelve a poner cuando hay algo que decir. Se envuelve en
un Frame para que, al volver a aparecer, quede en el mismo lugar y no al final.

El texto usa TODO el ancho disponible: el salto de línea se recalcula cada vez que
cambia el ancho del mensaje, así que sirve en cualquier pantalla.
"""
import ttkbootstrap as ttk

from simultradia.iu.styles import Colors, Fonts, Spacing


class StatusMessage(ttk.Frame):
    def __init__(self, parent, fuente: str = Fonts.BODY):
        super().__init__(parent)
        # Tk NO recalcula el tamaño de un contenedor que se queda sin ningún hijo: conserva
        # el último y el espacio del mensaje seguiría reservado. Esta tira invisible de
        # 1 píxel siempre presente evita que el contenedor quede vacío.
        ttk.Frame(self, height=1).pack(fill="x")
        self._etiqueta = ttk.Label(self, text="", justify="left", font=fuente)
        self.bind("<Configure>", self._ajustar_ancho)

    def mostrar_error(self, texto: str) -> None:
        self._mostrar(texto, Colors.DANGER)

    def mostrar_exito(self, texto: str) -> None:
        self._mostrar(texto, Colors.SUCCESS)

    def limpiar(self) -> None:
        self._etiqueta.pack_forget()

    def _mostrar(self, texto: str, color: str) -> None:
        if not texto:
            self.limpiar()
            return
        self._etiqueta.configure(text=texto, bootstyle=color)
        self._etiqueta.pack(anchor="w", fill="x", pady=(Spacing.XS, 0))

    def _ajustar_ancho(self, evento) -> None:
        if evento.width > 1:
            self._etiqueta.configure(wraplength=evento.width)
