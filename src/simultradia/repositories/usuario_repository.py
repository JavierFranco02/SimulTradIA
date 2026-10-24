"""Acceso a la tabla "usuarios". Aquí vive TODO el SQL relacionado con usuarios."""
from typing import Optional

import psycopg2

from simultradia.core.exceptions import EmailYaRegistrado
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.domain.enums import RolUsuario

_COLUMNAS = (
    "id_usuario, nombre, email, password_hash, rol, activo, "
    "ultimo_login_en, creado_en, actualizado_en"
)


class UsuarioRepository:
    """Cada método recibe la conexión (conn) que presta Database.obtener_conexion(),
    para que el servicio decida qué operaciones forman una misma transacción.

    Las filas llegan como namedtuple: se leen por nombre (`fila.email`), no por posición."""

    def buscar_por_email(self, conn, email: str) -> Optional[Usuario]:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT " + _COLUMNAS + " FROM usuarios WHERE lower(email) = lower(%s)",
                (email,),
            )
            fila = cur.fetchone()
        return self._a_entidad(fila) if fila else None

    def insertar(self, conn, usuario: Usuario) -> Usuario:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO usuarios (nombre, email, password_hash, rol, activo)
                       VALUES (%s, %s, %s, %s, %s)
                       RETURNING id_usuario, creado_en, actualizado_en""",
                    (usuario.nombre, usuario.email, usuario.password_hash,
                     usuario.rol.value, usuario.activo),
                )
                fila = cur.fetchone()
        except psycopg2.IntegrityError as error:
            # 23505 = valor duplicado. Pasa si dos personas registran el mismo email a la vez.
            if error.pgcode == "23505":
                raise EmailYaRegistrado() from error
            raise
        usuario.id_usuario = fila.id_usuario
        usuario.creado_en = fila.creado_en
        usuario.actualizado_en = fila.actualizado_en
        return usuario

    def registrar_login(self, conn, id_usuario: int) -> None:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE usuarios SET ultimo_login_en = now() WHERE id_usuario = %s",
                (id_usuario,),
            )

    @staticmethod
    def _a_entidad(fila) -> Usuario:
        """Convierte una fila de PostgreSQL (namedtuple) en un objeto Usuario."""
        return Usuario(
            id_usuario=fila.id_usuario,
            nombre=fila.nombre,
            email=fila.email,
            password_hash=fila.password_hash,
            rol=RolUsuario(fila.rol),
            activo=fila.activo,
            ultimo_login_en=fila.ultimo_login_en,
            creado_en=fila.creado_en,
            actualizado_en=fila.actualizado_en,
        )
