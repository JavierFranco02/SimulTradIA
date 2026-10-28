"""Base de los controladores de secciones (Mercado, ficha, administración...).

Reúne lo que todos hacen igual: correr el trabajo en segundo plano, descartar el resultado
si el usuario ya cambió de sección y mostrar los errores. Cada controlador hijo solo dice
QUÉ trabajo lanzar. (Los formularios usan FormController, que además maneja el botón ocupado.)
"""
import logging
from typing import Callable, Optional

from simultradia.core.exceptions import ErrorAplicacion
from simultradia.iu.background import ejecutar_en_hilo

_log = logging.getLogger(__name__)


class PanelController:
    def __init__(self, vista):
        self._vista = vista

    def _ejecutar(self, trabajo: Callable, al_terminar: Callable,
                  al_fallar: Optional[Callable] = None) -> None:
        def terminar(resultado) -> None:
            if self._vista.esta_viva():
                al_terminar(resultado)

        def fallar(error: Exception) -> None:
            if self._vista.esta_viva():
                (al_fallar or self._al_fallar)(error)

        ejecutar_en_hilo(trabajo, al_terminar=terminar, al_fallar=fallar)

    def _al_fallar(self, error: Exception) -> None:
        if isinstance(error, ErrorAplicacion):
            self._vista.mostrar_error(str(error))
        else:
            _log.error("Error inesperado", exc_info=error)
            self._vista.mostrar_error("Ocurrió un error inesperado. Inténtalo de nuevo.")
