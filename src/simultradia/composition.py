"""Armado de los servicios: UN solo lugar donde se conectan servicios y repositorios.

Lo usan main.py, worker.py y los scripts, para que ninguno repita el armado:

    db = Database(SETTINGS.database)
    servicios = crear_servicios(db)
    servicios.usuario.registrar(...)

Para agregar un servicio: súmalo a `Servicios` y a `crear_servicios`.
"""
from dataclasses import dataclass

from simultradia.repositories.cuenta_repository import CuentaRepository
from simultradia.repositories.usuario_repository import UsuarioRepository
from simultradia.services.usuario_service import UsuarioService


@dataclass(frozen=True)
class Servicios:
    usuario: UsuarioService


def crear_servicios(db) -> Servicios:
    return Servicios(
        usuario=UsuarioService(db, UsuarioRepository(), CuentaRepository()),
    )
