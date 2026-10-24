"""Base de los controladores de formularios (login, registro...).

Reúne lo que todos hacen igual: no dejar enviar dos veces, limpiar los errores
anteriores, lanzar el trabajo en segundo plano y mostrar los errores que lleguen,
cada uno donde corresponde. Cada controlador hijo solo dice QUÉ trabajo lanzar.
"""
import logging

from simultradia.core.exceptions import DatosInvalidos, ErrorAplicacion
from simultradia.iu.background import ejecutar_en_hilo

_log = logging.getLogger(__name__)


class FormController:
    def __init__(self, vista, usuario_service, navegador):
        self._vista = vista
        self._service = usuario_service
        self._navegador = navegador

    def _ejecutar(self, trabajo, al_terminar) -> None:
        """Corre `trabajo` en segundo plano.

        - Si sale bien y el usuario sigue en esta pantalla: llama a `al_terminar(resultado)`.
        - Si sale bien pero el usuario ya se fue a otra pantalla: se descarta el resultado
          (no navega ni toca la pantalla).
        - Si falla, se encarga `_al_fallar` (que también comprueba que la pantalla siga viva).
        """
        if self._vista.ocupado:
            return   # ya hay un intento en curso
        self._vista.limpiar_errores()
        self._vista.establecer_ocupado(True)

        def al_terminar_si_sigue_aqui(resultado) -> None:
            if self._vista.esta_viva():
                al_terminar(resultado)

        ejecutar_en_hilo(trabajo, al_terminar=al_terminar_si_sigue_aqui, al_fallar=self._al_fallar)

    def _al_fallar(self, error: Exception) -> None:
        if not self._vista.esta_viva():   # el usuario ya cambió de pantalla
            return
        self._vista.establecer_ocupado(False)
        if isinstance(error, DatosInvalidos):
            self._vista.mostrar_errores_campos(error.errores)   # cada mensaje bajo su campo
        elif isinstance(error, ErrorAplicacion):
            self._vista.mostrar_error(str(error))
        else:
            _log.error("Error inesperado", exc_info=error)
            self._vista.mostrar_error("Ocurrió un error inesperado. Inténtalo de nuevo.")
