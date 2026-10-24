"""Sección "inicio" (dentro del shell)."""
from simultradia.iu.inicio.inicio_view import InicioView


def _inicio(padre, nav):
    return InicioView(padre, nav.session.usuario)


def registrar(navegador) -> None:
    navegador.registrar("inicio", _inicio, en_shell=True)
