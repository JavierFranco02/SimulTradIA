from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from simultradia.domain.enums import RolUsuario


@dataclass
class Usuario:
    nombre: str
    email: str
    password_hash: str = field(repr=False)
    rol: RolUsuario = RolUsuario.USUARIO
    activo: bool = True
    id_usuario: Optional[int] = None
    ultimo_login_en: Optional[datetime] = None
    creado_en: Optional[datetime] = None
    actualizado_en: Optional[datetime] = None
    debe_cambiar_password: bool = False      # True mientras tenga una contraseña temporal entregada por el admin

    @property
    def es_admin(self) -> bool:
        return self.rol == RolUsuario.ADMIN
