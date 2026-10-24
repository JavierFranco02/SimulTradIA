"""Controlador del shell: cambia de sección desde el menú y cierra la sesión."""


class ShellController:
    def __init__(self, vista, session, navegador):
        self._session = session
        self._navegador = navegador
        vista.vincular_acciones(
            al_elegir_seccion=self.ir_a_seccion,
            al_cerrar_sesion=self.cerrar_sesion,
        )

    def ir_a_seccion(self, nombre: str) -> None:
        self._navegador.ir_a(nombre)

    def cerrar_sesion(self) -> None:
        self._session.cerrar()
        self._navegador.ir_a("login")
