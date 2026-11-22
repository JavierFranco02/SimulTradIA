"""Tarea: generar la predicción de volatilidad del día de cada activo con el modelo activo.
El worker la repite cada hora; si ya existe la de hoy, no repite nada."""
import logging

from simultradia.core.exceptions import ErrorAplicacion

_log = logging.getLogger(__name__)


def ejecutar(servicios) -> None:
    try:
        resultado = servicios.volatilidad.generar_predicciones()
        if resultado.generadas:
            _log.info("Predicciones de volatilidad generadas: %d (%d activos omitidos por falta de velas al día).",
                      resultado.generadas, resultado.omitidas)
    except ErrorAplicacion as error:
        _log.warning("No se generaron las predicciones de volatilidad: %s", error)
    except Exception:
        _log.exception("Falló la generación de predicciones de volatilidad")
