"""Proceso SIN ventanas que mantiene los datos de mercado al día y ejecuta las órdenes pendientes.

Se ejecuta en una terminal aparte, mientras la app está abierta:

    python worker.py

  - cada 2 segundos: precio actual de todos los activos (lo que ve Mercado y el gráfico en vivo) y,
    con esos precios, las órdenes límite que llegaron a su precio y los stop-loss / take-profit disparados
  - cada 60 segundos: velas nuevas (la primera vez descarga todo el historial; puede tardar) y la foto del
    patrimonio de cada cuenta (la curva de Portafolio; una fila por minuto)
  - cada hora: evalúa las predicciones de volatilidad vencidas y genera la del día (si ya hay un modelo activo)

Solo PROGRAMA cuándo corre cada tarea; el trabajo está en jobs/ y en los servicios.
Se detiene con Ctrl+C.
"""
import logging
import sys
import threading
import time

from simultradia.composition import crear_servicios
from simultradia.core.db import Database
from simultradia.core.exceptions import ErrorBaseDatos
from simultradia.core.logging_config import configurar_logging
from simultradia.core.settings import SETTINGS
from simultradia.jobs import (
    actualizar_cotizaciones_job, actualizar_velas_job, evaluar_ordenes_job, evaluar_volatilidad_job,
    generar_volatilidad_job, guardar_snapshots_job)

_log = logging.getLogger("worker")


def _tareas_de_ia(servicios) -> None:
    evaluar_volatilidad_job.ejecutar(servicios)
    generar_volatilidad_job.ejecutar(servicios)


def main() -> int:
    configurar_logging()
    try:
        db = Database(SETTINGS.database)
    except ErrorBaseDatos as error:
        _log.error("%s", error)
        return 1
    servicios = crear_servicios(db)

    ultima_pasada_velas = float("-inf")
    ultima_foto = float("-inf")
    hilo_velas = None
    ultima_pasada_ia = float("-inf")
    hilo_ia = None
    _log.info("Worker iniciado. Ctrl+C para detenerlo.")
    try:
        while True:
            inicio = time.monotonic()
            actualizar_cotizaciones_job.ejecutar(servicios)
            evaluar_ordenes_job.ejecutar(servicios)
            # La foto del patrimonio va después de los precios (usa los recién guardados) y es corta.
            if inicio - ultima_foto >= 60:
                guardar_snapshots_job.ejecutar(servicios)
                ultima_foto = inicio
            # Las velas van en su propio hilo: la primera descarga tarda y no debe frenar los precios.
            if inicio - ultima_pasada_velas >= 60 and not (hilo_velas and hilo_velas.is_alive()):
                hilo_velas = threading.Thread(
                    target=actualizar_velas_job.ejecutar, args=(servicios,), daemon=True)
                hilo_velas.start()
                ultima_pasada_velas = inicio
            # La IA también va aparte: leer 10 años de velas y predecir no debe frenar los precios.
            if inicio - ultima_pasada_ia >= 3600 and not (hilo_ia and hilo_ia.is_alive()):
                hilo_ia = threading.Thread(target=_tareas_de_ia, args=(servicios,), daemon=True)
                hilo_ia.start()
                ultima_pasada_ia = inicio
            time.sleep(max(0.0, 2.0 - (time.monotonic() - inicio)))
    except KeyboardInterrupt:
        _log.info("Worker detenido.")
    finally:
        db.cerrar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
