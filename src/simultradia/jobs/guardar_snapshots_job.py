"""Tarea: guardar la foto del patrimonio de cada cuenta (la curva de Portafolio). El worker la repite cada minuto."""
import logging

from simultradia.core.exceptions import ErrorAplicacion

_log = logging.getLogger(__name__)


def ejecutar(servicios) -> None:
    try:
        servicios.portafolio.guardar_snapshots()
    except ErrorAplicacion as error:    # base caída...: se reintenta en la próxima vuelta
        _log.warning("No se guardaron las fotos del patrimonio: %s", error)
    except Exception:                   # un fallo aquí no debe detener la actualización de precios
        _log.exception("Falló el guardado de las fotos del patrimonio")
