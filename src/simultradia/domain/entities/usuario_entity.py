"""La "ficha" de un usuario dentro del código (espejo de la tabla usuarios)."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from simultradia.domain.enums import RolUsuario


@dataclass
class Usuario:
    nombre: str
    email: str
    password_hash: str = field(repr=False)   # repr=False: no aparece al imprimir el objeto
    rol: RolUsuario = RolUsuario.USUARIO
    activo: bool = True
    id_usuario: Optional[int] = None         # lo asigna PostgreSQL al insertar
    ultimo_login_en: Optional[datetime] = None
    creado_en: Optional[datetime] = None
    actualizado_en: Optional[datetime] = None

    @property
    def es_admin(self) -> bool:
        return self.rol == RolUsuario.ADMIN
