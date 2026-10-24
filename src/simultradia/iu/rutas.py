"""Registro de TODAS las pantallas de la app.

Cada módulo de la interfaz tiene su `pantallas.py` con una función `registrar(navegador)`.
Para agregar un módulo nuevo: crea su carpeta en iu/ y suma una línea aquí.
"""
from simultradia.iu.auth import pantallas as auth
from simultradia.iu.inicio import pantallas as inicio
from simultradia.iu.shell import pantallas as shell


def registrar_pantallas(navegador) -> None:
    auth.registrar(navegador)
    shell.registrar(navegador)
    inicio.registrar(navegador)
