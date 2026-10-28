"""El shell ("home"): ventana principal con menú lateral y contenido intercambiable.

Para agregar una sección al menú: regístrala (con en_shell=True) en el pantallas.py de
su módulo y súmala a _MENU.
"""
from simultradia.iu.shell.shell_controller import ShellController
from simultradia.iu.shell.shell_view import ShellView

# (nombre de la pantalla, texto del botón, solo administrador)
_MENU = (
    ("inicio", "Inicio", False),
    ("mercado", "Mercado", False),
    ("admin_usuarios", "Usuarios", True),
    ("admin_activos", "Activos", True),
    ("admin_ingesta", "Ingesta de datos", True),
)


def _home(padre, nav):
    menu = [(nombre, texto) for nombre, texto, solo_admin in _MENU if not solo_admin]
    menu_admin = [(nombre, texto) for nombre, texto, solo_admin in _MENU
                  if solo_admin and nav.session.es_admin]
    vista = ShellView(padre, nav.session.usuario, menu, menu_admin)
    ShellController(vista, nav.session, nav)
    return vista


def registrar(navegador) -> None:
    navegador.registrar("home", _home, tamano=(1100, 700), minimo=(900, 600),
                        seccion_inicial="inicio")
