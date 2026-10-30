"""Pantallas de autenticación (a ventana completa): login, registro y cambio de contraseña temporal."""
from simultradia.iu.auth.cambiar_password_controller import CambiarPasswordController
from simultradia.iu.auth.cambiar_password_view import CambiarPasswordView
from simultradia.iu.auth.login_controller import LoginController
from simultradia.iu.auth.login_view import LoginView
from simultradia.iu.auth.registro_controller import RegistroController
from simultradia.iu.auth.registro_view import RegistroView

_TAMANO = (480, 720)
_MINIMO = (420, 660)


def _login(padre, nav, email: str = "", mensaje: str = ""):
    vista = LoginView(padre, email_inicial=email, mensaje_inicial=mensaje)
    LoginController(vista, nav.servicios.usuario, nav, nav.session)
    return vista


def _registro(padre, nav):
    vista = RegistroView(padre)
    RegistroController(vista, nav.servicios.usuario, nav)
    return vista


def _cambiar_password(padre, nav, email: str):
    vista = CambiarPasswordView(padre)
    CambiarPasswordController(vista, nav.servicios.usuario, nav, email)
    return vista


def registrar(navegador) -> None:
    navegador.registrar("login", _login, tamano=_TAMANO, minimo=_MINIMO)
    navegador.registrar("registro", _registro, tamano=_TAMANO, minimo=_MINIMO)
    navegador.registrar("cambiar_password", _cambiar_password, tamano=_TAMANO, minimo=_MINIMO)
