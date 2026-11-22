"""Pantalla del módulo IA (sección dentro del shell): escáner de volatilidad y detalle del activo."""
from simultradia.iu.ia.ia_controller import IAController
from simultradia.iu.ia.ia_view import IAView


def _ia(padre, nav):
    vista = IAView(padre)
    IAController(vista, nav.servicios.volatilidad).cargar()
    return vista


def registrar(navegador) -> None:
    navegador.registrar("ia", _ia, en_shell=True)
