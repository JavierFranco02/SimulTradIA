"""Controlador de la pantalla de login: el INTERMEDIARIO entre la vista y el servicio.

  Vista       -> avisa "el usuario pulsó Entrar"
  Controlador -> lee los campos, llama al servicio (en segundo plano) y, si todo sale
                  bien y el usuario sigue en esta pantalla, inicia la sesión y navega
  Servicio    -> solo VERIFICA el email y la contraseña y devuelve el usuario
"""
from simultradia.core.exceptions import CredencialesInvalidas
from simultradia.iu.base.form_controller import FormController


class LoginController(FormController):
    def __init__(self, vista, usuario_service, navegador, session):
        """`navegador` es el Navegador (debe tener ir_a(nombre, **parametros)). `session` es
        la sesión de la aplicación, que este controlador abre cuando el login es correcto."""
        super().__init__(vista, usuario_service, navegador)
        self._session = session
        vista.vincular_acciones(
            al_iniciar_sesion=self.iniciar_sesion,
            al_ir_a_registro=self.ir_a_registro,
        )

    def ir_a_registro(self) -> None:
        self._navegador.ir_a("registro")

    def iniciar_sesion(self) -> None:
        datos = self._vista.valores()
        email, password = datos["email"], datos["password"]
        self._ejecutar(
            lambda: self._service.autenticar(email, password),
            al_terminar=self._al_autenticar,
        )

    def _al_autenticar(self, usuario) -> None:
        # Solo se llega aquí si el usuario sigue en esta pantalla (lo garantiza _ejecutar),
        # así que la sesión nunca se abre "a escondidas" desde una pantalla que ya se dejó.
        if usuario.debe_cambiar_password:
            # Entró con una contraseña temporal: primero debe elegir una nueva. No se abre sesión.
            self._navegador.ir_a("cambiar_password", email=usuario.email)
            return
        self._session.iniciar(usuario)
        self._navegador.ir_a("home")

    def _al_fallar(self, error: Exception) -> None:
        super()._al_fallar(error)
        # Con una contraseña incorrecta, se borra la caja para escribirla de nuevo.
        if isinstance(error, CredencialesInvalidas) and self._vista.esta_viva():
            self._vista.limpiar_campo("password")
