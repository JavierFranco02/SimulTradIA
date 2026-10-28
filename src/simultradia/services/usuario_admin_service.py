"""Administración de usuarios: buscar, activar o desactivar cuentas y restablecer contraseñas.

Todo método recibe el `actor` (quien lo pide) y exige que sea administrador: los permisos
se validan aquí, no solo ocultando botones. Cambiar el rol y reiniciar cuentas se harán más
adelante (cambiar rol, al decidir qué pasa con la cuenta simulada; reiniciar, con las tablas
de operar). `UsuarioService` sigue con el login, el registro y el cambio de contraseña temporal.
"""
import secrets
from typing import List, Optional

from simultradia.core.exceptions import ErrorOperacionInvalida
from simultradia.core.security import hashear_password
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.services.permisos import exigir_admin

# Sin 0/O, 1/l/I y otros caracteres que se confunden al dictarlos o copiarlos a mano.
_ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
_LARGO_TEMPORAL = 10


class UsuarioAdminService:
    def __init__(self, db, usuario_repository):
        self._db = db
        self._usuarios = usuario_repository

    def listar(self, actor: Usuario, texto: str = "", rol: Optional[str] = None,
               activo: Optional[bool] = None) -> List[Usuario]:
        """Los usuarios, filtrados: `texto` busca en nombre y email; `rol` es "admin" o "usuario";
        `activo` True/False filtra por estado de la cuenta. Sin filtros devuelve todos."""
        exigir_admin(actor)
        with self._db.obtener_conexion() as conn:
            usuarios = self._usuarios.listar(conn)
        texto = (texto or "").strip().lower()
        return [u for u in usuarios
                if (not texto or texto in u.nombre.lower() or texto in u.email.lower())
                and (rol is None or u.rol.value == rol)
                and (activo is None or u.activo == activo)]

    def cambiar_estado(self, actor: Usuario, id_usuario: int, activo: bool) -> None:
        exigir_admin(actor)
        if not activo and id_usuario == actor.id_usuario:
            raise ErrorOperacionInvalida("No puedes desactivar tu propia cuenta.")
        with self._db.obtener_conexion() as conn:
            objetivo = self._usuarios.buscar_por_id(conn, id_usuario)
            if objetivo is None:
                raise ErrorOperacionInvalida("Ese usuario no existe.")
            if not activo and objetivo.es_admin:
                raise ErrorOperacionInvalida("No se puede desactivar a un administrador.")
            self._usuarios.establecer_activo(conn, id_usuario, activo)

    def restablecer_password(self, actor: Usuario, id_usuario: int) -> str:
        """Pone una contraseña TEMPORAL al usuario y la devuelve para que el admin se la entregue.

        Es la única vez que se conoce: en la base solo queda su hash. La contraseña que tenía
        deja de funcionar, y al iniciar sesión con la temporal el usuario debe elegir una nueva.
        El admin nunca ve la contraseña real de nadie. No se aplica a administradores (así nadie
        puede tomar la cuenta de otro admin)."""
        exigir_admin(actor)
        temporal = "".join(secrets.choice(_ALFABETO) for _ in range(_LARGO_TEMPORAL))
        with self._db.obtener_conexion() as conn:
            objetivo = self._usuarios.buscar_por_id(conn, id_usuario)
            if objetivo is None:
                raise ErrorOperacionInvalida("Ese usuario no existe.")
            if objetivo.es_admin:
                raise ErrorOperacionInvalida("No se puede restablecer la contraseña de un administrador desde aquí.")
            self._usuarios.actualizar_password(conn, id_usuario, hashear_password(temporal), True)
        return temporal
