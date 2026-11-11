"""Pantalla de inicio de sesión.

Es una vista "pasiva": solo dibuja y expone métodos para leer y mostrar datos.
No decide nada ni habla con servicios; eso lo hace LoginController.
"""
from tkinter import messagebox
from typing import Callable, Optional

from simultradia.core.settings import SETTINGS
from simultradia.iu.base.form_view import FormView
from simultradia.iu.components import (
    ActionButton,
    FormField,
    PasswordField,
    ShowPasswordToggle,
)
from simultradia.iu.styles import ButtonStyle, Spacing


class LoginView(FormView):
    def __init__(self, parent, email_inicial: str = "", mensaje_inicial: str = ""):
        super().__init__(parent, titulo=SETTINGS.app.name, subtitulo="Inicia sesión para continuar")
        self._al_iniciar_sesion: Optional[Callable[[], None]] = None
        self._al_ir_a_registro: Optional[Callable[[], None]] = None

        email = self._agregar_campo("email", FormField(self._cuerpo, "Email"))
        password = self._agregar_campo("password", PasswordField(self._cuerpo, "Contraseña"))
        ShowPasswordToggle(self._cuerpo, [password]).pack(anchor="w", pady=(Spacing.SM, 0))
        self._agregar_mensaje()
        self._agregar_boton_principal("Iniciar sesión", "Verificando...", self._pulsar_entrar)
        ActionButton(self._cuerpo, "¿No tienes cuenta? Regístrate", self._pulsar_registro,
                     estilo=ButtonStyle.LINK).pack()

        if email_inicial:
            email.establecer(email_inicial)
        if mensaje_inicial:
            # Confirmación ("¡Cuenta creada!"): un diálogo, no texto que se quede en el formulario.
            # Se abre con un pequeño retraso para que la ventana ya esté dibujada.
            self.after(200, lambda: self._avisar(mensaje_inicial))

        # Enter en el email pasa a la contraseña; Enter en la contraseña envía el formulario.
        email.al_presionar_enter(password.enfocar)
        password.al_presionar_enter(self._pulsar_entrar)
        (password if email_inicial else email).enfocar()

    def vincular_acciones(self, al_iniciar_sesion: Callable[[], None],
                          al_ir_a_registro: Callable[[], None]) -> None:
        self._al_iniciar_sesion = al_iniciar_sesion
        self._al_ir_a_registro = al_ir_a_registro

    def _avisar(self, texto: str) -> None:
        if self.esta_viva():   # el usuario pudo cambiar de pantalla antes del retraso
            messagebox.showinfo("Listo", texto, parent=self)

    def _pulsar_entrar(self) -> None:
        if self._al_iniciar_sesion:
            self._al_iniciar_sesion()

    def _pulsar_registro(self) -> None:
        if self._al_ir_a_registro:
            self._al_ir_a_registro()
