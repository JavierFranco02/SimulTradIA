"""Pantalla para elegir una contraseña nueva cuando se entró con una temporal (vista pasiva)."""
from typing import Callable, Optional

from simultradia.iu.base.form_view import FormView
from simultradia.iu.components import ActionButton, PasswordField, ShowPasswordToggle
from simultradia.iu.styles import ButtonStyle, Spacing


class CambiarPasswordView(FormView):
    def __init__(self, parent):
        super().__init__(parent, titulo="Elige tu contraseña",
                         subtitulo="La que recibiste es temporal: crea una nueva para continuar")
        self._al_guardar: Optional[Callable[[], None]] = None
        self._al_volver_a_login: Optional[Callable[[], None]] = None

        actual = self._agregar_campo("actual", PasswordField(self._cuerpo, "Contraseña temporal"))
        nueva = self._agregar_campo("password", PasswordField(self._cuerpo, "Contraseña nueva"))
        confirmacion = self._agregar_campo(
            "confirmacion", PasswordField(self._cuerpo, "Repite la contraseña nueva"))
        ShowPasswordToggle(
            self._cuerpo, [actual, nueva, confirmacion], texto="Mostrar contraseñas",
        ).pack(anchor="w", pady=(Spacing.SM, 0))
        self._agregar_mensaje()
        self._agregar_boton_principal("Guardar contraseña", "Guardando...", self._pulsar_guardar)
        ActionButton(self._cuerpo, "Volver al inicio de sesión", self._pulsar_volver,
                     estilo=ButtonStyle.LINK).pack()

        confirmacion.al_presionar_enter(self._pulsar_guardar)
        actual.enfocar()

    def vincular_acciones(self, al_guardar: Callable[[], None],
                          al_volver_a_login: Callable[[], None]) -> None:
        self._al_guardar = al_guardar
        self._al_volver_a_login = al_volver_a_login

    def _pulsar_guardar(self) -> None:
        if self._al_guardar:
            self._al_guardar()

    def _pulsar_volver(self) -> None:
        if self._al_volver_a_login:
            self._al_volver_a_login()
