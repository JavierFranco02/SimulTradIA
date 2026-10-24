"""Crea el primer administrador. Se ejecuta UNA vez, desde la carpeta del proyecto:

    python scripts/crear_admin.py

El administrador no se puede crear desde la pantalla de registro (a propósito),
por eso existe este script. Requiere haber hecho antes:  pip install -e .
"""
import getpass
import sys

from simultradia.composition import crear_servicios
from simultradia.core.db import Database
from simultradia.core.exceptions import ErrorAplicacion
from simultradia.core.logging_config import configurar_logging
from simultradia.core.settings import SETTINGS


def main() -> int:
    configurar_logging()
    print("=== Crear administrador ===")
    nombre = input("Nombre: ").strip()
    email = input("Email: ").strip()
    password = getpass.getpass("Contraseña (no se ve al escribir): ")
    confirmacion = getpass.getpass("Repite la contraseña: ")

    db = None
    try:
        db = Database(SETTINGS.database)
        servicios = crear_servicios(db)
        admin = servicios.usuario.crear_administrador(nombre, email, password, confirmacion)
    except ErrorAplicacion as error:
        print("Error: %s" % error)
        return 1
    finally:
        if db is not None:
            db.cerrar()

    print("Administrador creado: %s (id %s)" % (admin.email, admin.id_usuario))
    return 0


if __name__ == "__main__":
    sys.exit(main())
