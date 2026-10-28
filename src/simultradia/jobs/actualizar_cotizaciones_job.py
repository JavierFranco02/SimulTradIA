"""Tarea: traer el precio actual de todos los activos y guardarlo. El worker la repite cada pocos segundos."""
import logging

from simultradia.core.exceptions import ErrorAplicacion

_log = logging.getLogger(__name__)


def ejecutar(servicios) -> None:
    try:
        resultado = servicios.ingesta.actualizar_cotizaciones()
        if resultado.fallidos:
            _log.warning("Sin cotización: %s", ", ".join(resultado.fallidos))
    except ErrorAplicacion as error:   # sin internet, base caída...: se reintenta en la próxima vuelta
        _log.warning("No se actualizaron las cotizaciones: %s", error)
