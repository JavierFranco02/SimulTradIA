"""Ventana principal una vez iniciada la sesión: menú lateral fijo + área de contenido.

Vista pasiva. Las secciones (inicio, mercado...) se dibujan dentro de `contenido`;
quién las crea y las cambia es el Navegador. Cumple su protocolo:
    contenido                 -> Frame donde van las secciones
    marcar_seccion(nombre)    -> resalta la sección activa del menú
Los administradores ven, debajo del menú normal, un bloque "ADMINISTRACIÓN".
"""
from typing import Callable, Dict, Optional, Sequence, Tuple

import ttkbootstrap as ttk

from simultradia.core.settings import SETTINGS
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.iu.components import ActionButton
from simultradia.iu.styles import ButtonStyle, Colors, Fonts, Spacing


class ShellView(ttk.Frame):
    def __init__(self, parent, usuario: Usuario, menu: Sequence[Tuple[str, str]],
                 menu_admin: Sequence[Tuple[str, str]] = ()):
        """`menu` y `menu_admin` son listas de (nombre de la pantalla, texto del botón)."""
        super().__init__(parent)
        self._al_elegir_seccion: Optional[Callable[[str], None]] = None
        self._al_cerrar_sesion: Optional[Callable[[], None]] = None
        self._botones: Dict[str, ActionButton] = {}

        barra = ttk.Frame(self, padding=Spacing.MD)
        barra.pack(side="left", fill="y")
        ttk.Separator(self, orient="vertical").pack(side="left", fill="y")
        self.contenido = ttk.Frame(self, padding=Spacing.LG)
        self.contenido.pack(side="left", fill="both", expand=True)

        # El pie se empaqueta primero (side="bottom") para que quede abajo del todo.
        pie = ttk.Frame(barra)
        pie.pack(side="bottom", fill="x")
        ttk.Label(pie, text=usuario.nombre, font=Fonts.BODY).pack(anchor="w")
        ttk.Label(
            pie,
            text="Administrador" if usuario.es_admin else "Usuario",
            font=Fonts.SMALL,
            bootstyle=Colors.SUCCESS if usuario.es_admin else Colors.MUTED,
        ).pack(anchor="w", pady=(0, Spacing.SM))
        ActionButton(pie, "Cerrar sesión", self._pulsar_cerrar_sesion,
                     estilo=ButtonStyle.DANGER_OUTLINE).pack(fill="x")

        ttk.Label(barra, text=SETTINGS.app.name, font=Fonts.HEADING,
                  bootstyle=Colors.PRIMARY).pack(anchor="w", pady=(0, Spacing.LG))
        self._agregar_botones(barra, menu)
        if menu_admin:
            ttk.Label(barra, text="ADMINISTRACIÓN", font=Fonts.SMALL,
                      bootstyle=Colors.MUTED).pack(anchor="w", pady=(Spacing.LG, Spacing.XS))
            self._agregar_botones(barra, menu_admin)

    def _agregar_botones(self, barra, menu: Sequence[Tuple[str, str]]) -> None:
        for nombre, etiqueta in menu:
            boton = ActionButton(barra, etiqueta, lambda n=nombre: self._pulsar_seccion(n),
                                 estilo=ButtonStyle.LINK)
            boton.pack(fill="x", pady=Spacing.XS)
            self._botones[nombre] = boton

    def vincular_acciones(self, al_elegir_seccion: Callable[[str], None],
                          al_cerrar_sesion: Callable[[], None]) -> None:
        self._al_elegir_seccion = al_elegir_seccion
        self._al_cerrar_sesion = al_cerrar_sesion

    def marcar_seccion(self, nombre: str) -> None:
        for clave, boton in self._botones.items():
            boton.configure(bootstyle=ButtonStyle.PRIMARY if clave == nombre else ButtonStyle.LINK)

    def _pulsar_seccion(self, nombre: str) -> None:
        if self._al_elegir_seccion:
            self._al_elegir_seccion(nombre)

    def _pulsar_cerrar_sesion(self) -> None:
        if self._al_cerrar_sesion:
            self._al_cerrar_sesion()
