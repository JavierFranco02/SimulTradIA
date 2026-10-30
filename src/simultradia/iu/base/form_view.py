"""Base de las pantallas con formulario (login, registro...).

Reúne lo que todas comparten: el título centrado, el registro de campos, el botón
principal, el mensaje general y los errores por campo. Cada pantalla hija solo
dice QUÉ campos y botones tiene.

El formulario va dentro de una "tarjeta" con borde y con un fondo distinto al de la
ventana, para que no parezca que ocupa toda la pantalla cuando esta se agranda.
"""
from typing import Dict, Optional

import ttkbootstrap as ttk

from simultradia.iu.components import ActionButton, FormField, StatusMessage
from simultradia.iu.styles import Colors, Fonts, Spacing


class FormView(ttk.Frame):
    def __init__(self, parent, titulo: str, subtitulo: str = ""):
        super().__init__(parent, padding=Spacing.LG, bootstyle=Colors.SURFACE)
        self._campos: Dict[str, FormField] = {}
        self._mensaje: Optional[StatusMessage] = None
        self._boton_principal: Optional[ActionButton] = None

        borde = ttk.Frame(self, padding=1, bootstyle=Colors.MUTED)   # línea de 1 px alrededor
        borde.pack(expand=True)     # sin fill => la tarjeta queda centrada y no se estira
        tarjeta = ttk.Frame(borde, padding=Spacing.LG)
        tarjeta.pack()
        ttk.Label(tarjeta, text=titulo, font=Fonts.TITLE, bootstyle=Colors.PRIMARY).pack()
        if subtitulo:
            ttk.Label(tarjeta, text=subtitulo, font=Fonts.SUBTITLE,
                      bootstyle=Colors.MUTED).pack(pady=(2, Spacing.LG))
        self._cuerpo = ttk.Frame(tarjeta)   # aquí se agregan los campos y botones
        self._cuerpo.pack(fill="x")

    # --- para que las pantallas hijas armen su formulario -------------------
    def _agregar_campo(self, clave: str, campo: FormField) -> FormField:
        """`clave` es el nombre con el que el servicio identifica este campo
        en sus errores (por ejemplo "email" o "password")."""
        campo.pack(fill="x")
        self._campos[clave] = campo
        return campo

    def _agregar_mensaje(self) -> StatusMessage:
        self._mensaje = StatusMessage(self._cuerpo)
        self._mensaje.pack(fill="x")
        return self._mensaje

    def _agregar_boton_principal(self, texto: str, texto_ocupado: str, comando) -> None:
        self._boton_principal = ActionButton(self._cuerpo, texto, comando, texto_ocupado)
        self._boton_principal.pack(fill="x", pady=(Spacing.MD, Spacing.SM), ipady=4)

    # --- lo que el controlador puede leer y ordenar -------------------------
    def valores(self) -> Dict[str, str]:
        """Lo escrito en cada campo, por clave: {"email": "...", "password": "..."}."""
        return {clave: campo.obtener() for clave, campo in self._campos.items()}

    @property
    def ocupado(self) -> bool:
        return self._boton_principal.ocupado

    def establecer_ocupado(self, ocupado: bool) -> None:
        self._boton_principal.establecer_ocupado(ocupado)

    def mostrar_error(self, texto: str) -> None:
        """Error general del formulario (no de un campo concreto)."""
        self._mensaje.mostrar_error(texto)

    def mostrar_errores_campos(self, errores: Dict[str, str]) -> None:
        """Pone cada mensaje debajo de su campo. Si llega un campo que esta pantalla
        no tiene, el mensaje se muestra como error general para que no se pierda."""
        for clave, texto in errores.items():
            campo = self._campos.get(clave)
            if campo is None:
                self._mensaje.mostrar_error(texto)
            else:
                campo.mostrar_error(texto)

    def limpiar_errores(self) -> None:
        self._mensaje.limpiar()
        for campo in self._campos.values():
            campo.ocultar_error()

    def limpiar_campo(self, clave: str) -> None:
        self._campos[clave].limpiar()
        self._campos[clave].enfocar()

    def esta_viva(self) -> bool:
        """False si el usuario ya cambió de pantalla y esta vista fue destruida."""
        return bool(self.winfo_exists())
