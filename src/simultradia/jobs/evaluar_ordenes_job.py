"""Tarea: ejecutar las órdenes límite que ya llegaron a su precio y los stop-loss / take-profit disparados.
El worker la repite cada pocos segundos, justo después de actualizar los precios."""
import logging

from simultradia.core.exceptions import ErrorAplicacion

_log = logging.getLogger(__name__)


def ejecutar(servicios) -> None:
    try:
        resultado = servicios.operar.evaluar_pendientes()
        if resultado.ejecutadas or resultado.rechazadas:
            _log.info("Órdenes pendientes: %d ejecutadas, %d rechazadas.",
                      resultado.ejecutadas, resultado.rechazadas)
    except ErrorAplicacion as error:    # base caída...: se reintenta en la próxima vuelta
        _log.warning("No se evaluaron las órdenes pendientes: %s", error)
    except Exception:                   # un fallo aquí no debe detener la actualización de precios
        _log.exception("Falló la evaluación de órdenes pendientes")
