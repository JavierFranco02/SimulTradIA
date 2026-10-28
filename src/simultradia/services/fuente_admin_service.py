"""Administración de las fuentes de datos: ver cuáles hay y habilitarlas o deshabilitarlas.

Una fuente deshabilitada deja de actualizar sus activos (sus últimos precios se quedan guardados).
Todo método recibe el `actor` y exige que sea administrador.
"""
from typing import List

from simultradia.core.exceptions import ErrorOperacionInvalida
from simultradia.domain.entities.fuente_entity import Fuente
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.services.permisos import exigir_admin


class FuenteAdminService:
    def __init__(self, db, fuente_repository):
        self._db = db
        self._fuentes = fuente_repository

    def listar(self, actor: Usuario) -> List[Fuente]:
        exigir_admin(actor)
        with self._db.obtener_conexion() as conn:
            return self._fuentes.listar(conn)

    def cambiar_estado(self, actor: Usuario, id_fuente: int, activa: bool) -> None:
        exigir_admin(actor)
        with self._db.obtener_conexion() as conn:
            if not self._fuentes.establecer_activa(conn, id_fuente, activa):
                raise ErrorOperacionInvalida("Esa fuente no existe.")
