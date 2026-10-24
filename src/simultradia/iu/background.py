"""Ejecutar trabajos lentos sin congelar la ventana.

tkinter solo permite tocar los widgets desde el hilo principal. Por eso el
trabajo corre en un hilo aparte y su resultado vuelve por una cola, que el hilo
principal revisa cada pocos milisegundos.

    ejecutar_en_hilo(lambda: servicio.hacer_algo(), al_terminar=..., al_fallar=...)

Es de la interfaz (usa `after` de tkinter). Las tareas programadas del worker
viven en `jobs/`, no aquí.
"""
import logging
import queue
import threading
from typing import Any, Callable, Optional

_log = logging.getLogger(__name__)
_cola: "queue.Queue" = queue.Queue()


def ejecutar_en_hilo(
    trabajo: Callable[[], Any],
    al_terminar: Optional[Callable[[Any], None]] = None,
    al_fallar: Optional[Callable[[Exception], None]] = None,
) -> None:
    def _correr() -> None:
        try:
            resultado = trabajo()
        except Exception as error:
            _cola.put((al_fallar, error, True))
        else:
            _cola.put((al_terminar, resultado, False))

    threading.Thread(target=_correr, daemon=True).start()


def iniciar_revision(raiz, cada_ms: int = 100) -> None:
    """Se llama UNA vez al arrancar la app. Entrega los resultados al hilo principal."""

    def _revisar() -> None:
        try:
            while True:
                try:
                    callback, valor, fue_error = _cola.get_nowait()
                except queue.Empty:
                    break
                if callback is None:
                    if fue_error:
                        _log.error("Falló una tarea en segundo plano", exc_info=valor)
                    continue
                try:
                    callback(valor)
                except Exception:
                    _log.exception("Error al procesar el resultado de una tarea")
        finally:
            raiz.after(cada_ms, _revisar)

    _revisar()
