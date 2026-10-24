"""El shell ("home"): ventana principal con menú lateral y contenido intercambiable.

Para agregar una sección al menú: regístrala (con en_shell=True) en el pantallas.py de
su módulo y súmala a _MENU.
"""
from simultradia.iu.shell.shell_controller import ShellController
from simultradia.iu.shell.shell_view import ShellView

# (nombre de la pantalla, texto del botón, solo administrador)
_MENU = (
    ("inicio", "Inicio", False),
)


def _home(padre, nav):
    menu = [(nombre, texto) for nombre, texto, solo_admin in _MENU
            if nav.session.es_admin or not solo_admin]
    vista = ShellView(padre, nav.session.usuario, menu)
    ShellController(vista, nav.session, nav)
    return vista


def registrar(navegador) -> None:
    navegador.registrar("home", _home, tamano=(1100, 700), minimo=(900, 600),
                        seccion_inicial="inicio")
