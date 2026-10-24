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
from simultradia.core.exceptions import ErrorBaseDatos
from simultradia.core.logging_config import configurar_logging
from simultradia.core.settings import SETTINGS


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
        App(crear_servicios(db)).mainloop()
    finally:
        db.cerrar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
