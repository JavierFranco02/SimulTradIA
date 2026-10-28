"""Tarea: descargar las velas que faltan (y la primera vez, todo el historial). El worker la repite cada minuto."""
import logging

from simultradia.core.exceptions import ErrorAplicacion

_log = logging.getLogger(__name__)


def ejecutar(servicios) -> None:
    try:
        resultado = servicios.ingesta.actualizar_velas()
        _log.info("Velas actualizadas: %d correctas, %d con error.",
                  resultado.correctos, len(resultado.fallidos))
    except ErrorAplicacion as error:
        _log.warning("No se actualizaron las velas: %s", error)
