"""Controlador de la pantalla de registro."""
from simultradia.iu.base.form_controller import FormController


class RegistroController(FormController):
    def __init__(self, vista, usuario_service, navegador):
        """`navegador` es el Navegador (debe tener ir_a(nombre, **parametros))."""
        super().__init__(vista, usuario_service, navegador)
        vista.vincular_acciones(
            al_registrar=self.registrar,
            al_volver_a_login=self.volver_a_login,
        )

    def volver_a_login(self) -> None:
        self._navegador.ir_a("login")

    def registrar(self) -> None:
        datos = self._vista.valores()
        nombre, email = datos["nombre"], datos["email"]
        password, confirmacion = datos["password"], datos["confirmacion"]
        self._ejecutar(
            lambda: self._service.registrar(nombre, email, password, confirmacion),
            al_terminar=self._al_registrar,
        )

    def _al_registrar(self, usuario) -> None:
        self._navegador.ir_a(
            "login", email=usuario.email, mensaje="¡Cuenta creada! Ya puedes iniciar sesión.")
