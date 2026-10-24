"""Conexión a PostgreSQL (con psycopg2, compatible con PostgreSQL 9.3).

Usa un "pool": un pequeño grupo de conexiones abiertas que se reutilizan, para
no abrir una conexión nueva en cada consulta.

Todos los cursores devuelven las filas como "namedtuple": se leen por NOMBRE de
columna (`fila.id_usuario`), nunca por posición, para que cambiar el orden de un
SELECT no rompa nada.
"""
import logging
from contextlib import contextmanager

import psycopg2
from psycopg2 import pool
from psycopg2.extras import NamedTupleCursor

from simultradia.core.exceptions import ErrorBaseDatos
from simultradia.core.settings import DatabaseSettings

_log = logging.getLogger(__name__)


class Database:
    def __init__(self, settings: DatabaseSettings):
        try:
            self._pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=5,
                host=settings.host,
                port=settings.port,
                dbname=settings.name,
                user=settings.user,
                password=settings.password,
                connect_timeout=5,
                client_encoding="UTF8",
                cursor_factory=NamedTupleCursor,
            )
        # UnicodeDecodeError: en Windows en español, algunos mensajes de error de
        # PostgreSQL llegan mal codificados y psycopg2 falla al leerlos.
        except (psycopg2.Error, UnicodeDecodeError) as error:
            _log.error("No se pudo conectar con PostgreSQL: %r", error)
            raise ErrorBaseDatos(
                "No se pudo conectar con la base de datos.\n"
                "Revisa que PostgreSQL esté encendido y que los datos del "
                "archivo .env sean correctos."
            ) from error

    @contextmanager
    def obtener_conexion(self):
        """Presta una conexión del pool para usarla dentro de un `with`:

            with db.obtener_conexion() as conn:
                repositorio.insertar(conn, ...)

        Al salir del `with`:
          - si todo salió bien, guarda los cambios (commit);
          - si hubo un error, los deshace (rollback);
          - en ambos casos devuelve la conexión al pool.
        Todo lo que se haga dentro del `with` es UNA sola operación: o se guarda
        completo o no se guarda nada.
        """
        try:
            conn = self._pool.getconn()
        except pool.PoolError as error:
            raise ErrorBaseDatos("Hay demasiadas operaciones en curso. Inténtalo de nuevo.") from error

        try:
            yield conn
            conn.commit()
        except psycopg2.OperationalError as error:
            self._deshacer(conn)
            _log.error("Se perdió la conexión: %r", error)
            raise ErrorBaseDatos("Se perdió la conexión con la base de datos.") from error
        except Exception:
            self._deshacer(conn)
            raise
        finally:
            self._pool.putconn(conn)

    @staticmethod
    def _deshacer(conn) -> None:
        try:
            conn.rollback()
        except Exception:  # la conexión puede estar ya cerrada
            pass

    def cerrar(self) -> None:
        self._pool.closeall()
