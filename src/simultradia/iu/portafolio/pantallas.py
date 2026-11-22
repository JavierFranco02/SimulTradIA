"""Sección "portafolio" (dentro del shell): cómo le va a la cuenta (curva de capital, métricas y operaciones cerradas)."""
from simultradia.iu.portafolio.portafolio_controller import PortafolioController
from simultradia.iu.portafolio.portafolio_view import PortafolioView


def _portafolio(padre, nav):
    vista = PortafolioView(padre)
    PortafolioController(vista, nav.servicios.portafolio, nav.session).cargar()
    return vista


def registrar(navegador) -> None:
    navegador.registrar("portafolio", _portafolio, en_shell=True)
