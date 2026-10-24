"""Pantallas de autenticación (a ventana completa): login y registro."""
from simultradia.iu.auth.login_controller import LoginController
from simultradia.iu.auth.login_view import LoginView
from simultradia.iu.auth.registro_controller import RegistroController
from simultradia.iu.auth.registro_view import RegistroView

_TAMANO = (480, 660)
_MINIMO = (420, 600)


def _login(padre, nav, email: str = "", mensaje: str = ""):
    vista = LoginView(padre, email_inicial=email, mensaje_inicial=mensaje)
    LoginController(vista, nav.servicios.usuario, nav, nav.session)
    return vista


def _registro(padre, nav):
    vista = RegistroView(padre)
    RegistroController(vista, nav.servicios.usuario, nav)
    return vista


def registrar(navegador) -> None:
    navegador.registrar("login", _login, tamano=_TAMANO, minimo=_MINIMO)
    navegador.registrar("registro", _registro, tamano=_TAMANO, minimo=_MINIMO)
