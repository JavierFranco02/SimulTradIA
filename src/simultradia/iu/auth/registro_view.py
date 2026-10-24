"""Pantalla para crear una cuenta nueva (vista pasiva; la lógica está en RegistroController)."""
from typing import Callable, Optional

from simultradia.iu.base.form_view import FormView
from simultradia.iu.components import (
    ActionButton,
    FormField,
    PasswordField,
    ShowPasswordToggle,
)
from simultradia.iu.styles import ButtonStyle, Spacing


class RegistroView(FormView):
    def __init__(self, parent):
        super().__init__(parent, titulo="Crear cuenta", subtitulo="Completa tus datos para empezar")
        self._al_registrar: Optional[Callable[[], None]] = None
        self._al_volver_a_login: Optional[Callable[[], None]] = None

        nombre = self._agregar_campo("nombre", FormField(self._cuerpo, "Nombre"))
        self._agregar_campo("email", FormField(self._cuerpo, "Email"))
        password = self._agregar_campo("password", PasswordField(self._cuerpo, "Contraseña"))
        confirmacion = self._agregar_campo(
            "confirmacion", PasswordField(self._cuerpo, "Repite la contraseña"))
        ShowPasswordToggle(
            self._cuerpo, [password, confirmacion], texto="Mostrar contraseñas",
        ).pack(anchor="w", pady=(Spacing.SM, 0))
        self._agregar_mensaje()
        self._agregar_boton_principal("Crear cuenta", "Creando cuenta...", self._pulsar_crear)
        ActionButton(self._cuerpo, "¿Ya tienes cuenta? Inicia sesión", self._pulsar_volver,
                     estilo=ButtonStyle.LINK).pack()

        confirmacion.al_presionar_enter(self._pulsar_crear)
        nombre.enfocar()

    def vincular_acciones(self, al_registrar: Callable[[], None],
                          al_volver_a_login: Callable[[], None]) -> None:
        self._al_registrar = al_registrar
        self._al_volver_a_login = al_volver_a_login

    def _pulsar_crear(self) -> None:
        if self._al_registrar:
            self._al_registrar()

    def _pulsar_volver(self) -> None:
        if self._al_volver_a_login:
            self._al_volver_a_login()
