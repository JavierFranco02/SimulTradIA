"""Proceso SIN ventanas que mantiene los datos de mercado al día.

Se ejecuta en una terminal aparte, mientras la app está abierta:

    python worker.py

  - cada 2 segundos: precio actual de todos los activos (lo que ve Mercado y el gráfico en vivo)
  - cada 60 segundos: velas nuevas (la primera vez descarga todo el historial; puede tardar)

Solo PROGRAMA cuándo corre cada tarea; el trabajo está en jobs/ y en IngestaService.
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
from simultradia.jobs import actualizar_cotizaciones_job, actualizar_velas_job

_log = logging.getLogger("worker")


def main() -> int:
    configurar_logging()
    try:
        db = Database(SETTINGS.database)
    except ErrorBaseDatos as error:
        _log.error("%s", error)
        return 1
    servicios = crear_servicios(db)

    ultima_pasada_velas = float("-inf")
    hilo_velas = None
    _log.info("Worker iniciado. Ctrl+C para detenerlo.")
    try:
        while True:
            inicio = time.monotonic()
            actualizar_cotizaciones_job.ejecutar(servicios)
            # Las velas van en su propio hilo: la primera descarga tarda y no debe frenar los precios.
            if inicio - ultima_pasada_velas >= 60 and not (hilo_velas and hilo_velas.is_alive()):
                hilo_velas = threading.Thread(
                    target=actualizar_velas_job.ejecutar, args=(servicios,), daemon=True)
                hilo_velas.start()
                ultima_pasada_velas = inicio
            time.sleep(max(0.0, 2.0 - (time.monotonic() - inicio)))
    except KeyboardInterrupt:
        _log.info("Worker detenido.")
    finally:
        db.cerrar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
