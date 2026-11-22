"""Borra las velas diarias (1d) para que el worker las vuelva a bajar con la historia completa.

Se ejecuta UNA vez, después de subir GUARDADOS de 1d a 3 650 días (10 años). Cambiar ese valor
solo no basta: el worker pide únicamente lo que falta desde la última vela guardada.

    python scripts/recargar_velas_diarias.py
    python worker.py          # la primera pasada tarda: baja 10 años de cada activo

Requiere haber hecho antes:  pip install -e .
Usa el repositorio directamente porque es una tarea de mantenimiento de una sola vez.
"""
import sys

from simultradia.core.db import Database
from simultradia.core.exceptions import ErrorAplicacion
from simultradia.core.logging_config import configurar_logging
from simultradia.core.settings import SETTINGS
from simultradia.domain.enums import IntervaloVela
from simultradia.repositories.precio_repository import PrecioRepository


def main() -> int:
    configurar_logging()
    print("Se borrarán TODAS las velas diarias (1d) de TODOS los activos.")
    print("Las de 15m y 1h no se tocan. El worker las volverá a bajar (10 años).")
    if input("Escribe SI para continuar: ").strip() != "SI":
        print("Cancelado.")
        return 0

    db = None
    try:
        db = Database(SETTINGS.database)
        with db.obtener_conexion() as conn:
            borradas = PrecioRepository().borrar_velas_de_intervalo(conn, IntervaloVela.D1)
    except ErrorAplicacion as error:
        print("Error: %s" % error)
        return 1
    finally:
        if db is not None:
            db.cerrar()

    print("Velas diarias borradas: %d. Ahora ejecuta:  python worker.py" % borradas)
    return 0


if __name__ == "__main__":
    sys.exit(main())
