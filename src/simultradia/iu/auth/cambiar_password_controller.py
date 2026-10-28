"""Controlador de la pantalla para cambiar la contraseña temporal."""
from simultradia.core.exceptions import CredencialesInvalidas
from simultradia.iu.base.form_controller import FormController


class CambiarPasswordController(FormController):
    def __init__(self, vista, usuario_service, navegador, email: str):
        """`email` es el de la cuenta que acaba de entrar con la contraseña temporal."""
        super().__init__(vista, usuario_service, navegador)
        self._email = email
        vista.vincular_acciones(al_guardar=self.guardar, al_volver_a_login=self.volver_a_login)

    def volver_a_login(self) -> None:
        self._navegador.ir_a("login")

    def guardar(self) -> None:
        datos = self._vista.valores()
        actual, nueva, confirmacion = datos["actual"], datos["password"], datos["confirmacion"]
        self._ejecutar(
            lambda: self._service.cambiar_password_temporal(self._email, actual, nueva, confirmacion),
            al_terminar=self._al_guardar,
        )

    def _al_guardar(self, usuario) -> None:
        self._navegador.ir_a(
            "login", email=usuario.email, mensaje="Contraseña actualizada. Ya puedes iniciar sesión.")

    def _al_fallar(self, error: Exception) -> None:
        super()._al_fallar(error)
        if isinstance(error, CredencialesInvalidas) and self._vista.esta_viva():
            self._vista.limpiar_campo("actual")
