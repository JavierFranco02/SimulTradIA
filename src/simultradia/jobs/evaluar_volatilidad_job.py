"""Tarea: completar las predicciones de volatilidad que ya vencieron (rango real, nivel real y si se acertó).
El worker la repite cada hora."""
import logging

from simultradia.core.exceptions import ErrorAplicacion

_log = logging.getLogger(__name__)


def ejecutar(servicios) -> None:
    try:
        evaluadas = servicios.volatilidad.evaluar_vencidas()
        if evaluadas:
            _log.info("Predicciones de volatilidad evaluadas: %d.", evaluadas)
    except ErrorAplicacion as error:
        _log.warning("No se evaluaron las predicciones de volatilidad: %s", error)
    except Exception:
        _log.exception("Falló la evaluación de predicciones de volatilidad")
