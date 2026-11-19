"""Tarea: completar las predicciones de IA que ya vencieron (qué pasó de verdad y si se acertó).
El worker la repite cada hora."""
import logging

from simultradia.core.exceptions import ErrorAplicacion

_log = logging.getLogger(__name__)


def ejecutar(servicios) -> None:
    try:
        evaluadas = servicios.prediccion.evaluar_vencidas()
        if evaluadas:
            _log.info("Predicciones evaluadas: %d.", evaluadas)
    except ErrorAplicacion as error:
        _log.warning("No se evaluaron las predicciones: %s", error)
    except Exception:
        _log.exception("Falló la evaluación de predicciones")
