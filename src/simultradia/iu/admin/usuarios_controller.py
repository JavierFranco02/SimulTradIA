"""Controlador de Administración · Usuarios: buscar, activar/desactivar y restablecer contraseñas."""
from simultradia.iu.base.panel_controller import PanelController


class UsuariosController(PanelController):
    def __init__(self, vista, usuario_admin_service, session):
        super().__init__(vista)
        self._servicio = usuario_admin_service
        self._session = session
        self._solicitud = 0    # número de la última petición: las respuestas viejas se descartan
        vista.vincular_acciones(al_filtrar=self.cargar, al_cambiar_estado=self.cambiar_estado,
                                al_restablecer=self.restablecer_password)

    def cargar(self) -> None:
        self._solicitud += 1
        numero, actor = self._solicitud, self._session.usuario
        texto, rol, activo = self._vista.filtros()
        self._ejecutar(lambda: self._servicio.listar(actor, texto, rol, activo),
                       al_terminar=lambda usuarios: self._al_cargar(numero, usuarios))

    def cambiar_estado(self, id_usuario: int, activar: bool) -> None:
        if not activar and not self._vista.confirmar(
                "¿Desactivar esta cuenta? La persona no podrá iniciar sesión."):
            return
        actor = self._session.usuario
        self._vista.limpiar_mensaje()
        self._ejecutar(lambda: self._servicio.cambiar_estado(actor, id_usuario, activar),
                       al_terminar=lambda _resultado: self.cargar())

    def restablecer_password(self, id_usuario: int) -> None:
        if not self._vista.confirmar("¿Restablecer la contraseña de esta cuenta? Su contraseña actual "
                                     "dejará de funcionar y recibirás una temporal para entregarle."):
            return
        actor = self._session.usuario
        self._vista.limpiar_mensaje()
        self._ejecutar(lambda: self._servicio.restablecer_password(actor, id_usuario),
                       al_terminar=lambda password: self._al_restablecer(id_usuario, password))

    # --------------------------------------------------------------- interno
    def _al_cargar(self, numero: int, usuarios) -> None:
        if numero == self._solicitud:
            self._vista.mostrar_usuarios(usuarios)

    def _al_restablecer(self, id_usuario: int, password: str) -> None:
        self._vista.mostrar_contrasena_temporal(id_usuario, password)
        self.cargar()    # la tabla pasa a mostrar "Temporal" en esa cuenta
