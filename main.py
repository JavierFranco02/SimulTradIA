"""Punto de entrada de la aplicación de escritorio.

Se ejecuta con:  python main.py
(antes, una sola vez:  pip install -e .)
"""
import sys
import tkinter as tk
from tkinter import messagebox

from simultradia.app import App
from simultradia.composition import crear_servicios
from simultradia.core.db import Database
from simultradia.core.exceptions import ErrorBaseDatos, ErrorOperacionInvalida  # DEBUG: + ErrorOperacionInvalida
from simultradia.core.logging_config import configurar_logging
from simultradia.core.settings import SETTINGS
from simultradia.debug_login import usuario_debug_desde_argumentos  # DEBUG


def main() -> int:
    configurar_logging()
    try:
        db = Database(SETTINGS.database)
    except ErrorBaseDatos as error:
        raiz = tk.Tk()          # aún no hay ventana de la app: se usa una oculta para el aviso
        raiz.withdraw()
        messagebox.showerror("No se pudo conectar", str(error), parent=raiz)
        raiz.destroy()
        return 1

    try:
        usuario_debug = usuario_debug_desde_argumentos(db)  # DEBUG
        App(crear_servicios(db), usuario_debug).mainloop()  # DEBUG: + usuario_debug
    except ErrorOperacionInvalida as error:  # DEBUG
        print("Error: %s" % error)  # DEBUG
        return 1  # DEBUG
    finally:
        db.cerrar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
