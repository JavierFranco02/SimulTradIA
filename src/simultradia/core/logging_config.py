"""Configuración de logs compartida por main.py, worker.py y los scripts."""
import logging


def configurar_logging(nivel: int = logging.INFO) -> None:
    """Se llama UNA vez, al arrancar cada programa."""
    logging.basicConfig(
        level=nivel,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
