"""Control de permisos. Lo usan los servicios de administración.

Los permisos se validan en el SERVICIO (no basta con ocultar botones). Todo método
de administración recibe quién lo pide (`actor`, normalmente `session.usuario`):

    def desactivar_usuario(self, actor: Usuario, id_usuario: int) -> None:
        exigir_admin(actor)
        ...
"""
from typing import Optional

from simultradia.core.exceptions import ErrorPermisos
from simultradia.domain.entities.usuario_entity import Usuario


def exigir_admin(actor: Optional[Usuario]) -> None:
    if actor is None or not actor.es_admin:
        raise ErrorPermisos()
