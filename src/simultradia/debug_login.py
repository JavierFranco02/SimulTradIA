"""SOLO PARA DEPURAR: entrar directo con un usuario, sin pasar por el login.

    python main.py --usuario demo@correo.com
    python main.py -u demo@correo.com           (forma corta)
    python main.py -u 3                         (por id)

No verifica contraseña ni cambia nada en la base. Para quitarlo: borra este archivo y las líneas
marcadas con "# DEBUG" en main.py y app.py.
"""
import sys
from typing import Optional

from simultradia.core.exceptions import ErrorOperacionInvalida
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.repositories.usuario_repository import UsuarioRepository


def usuario_debug_desde_argumentos(db) -> Optional[Usuario]:
    """El usuario pedido con --usuario (email o id), o None si no se pasó el argumento."""
    argumentos = sys.argv[1:]
    posicion = next((i for i, a in enumerate(argumentos) if a in ("--usuario", "-u")), None)
    if posicion is None:
        return None
    if posicion + 1 >= len(argumentos):
        raise ErrorOperacionInvalida("Falta el valor: -u <email o id>")
    valor = argumentos[posicion + 1].strip()
    repositorio = UsuarioRepository()
    with db.obtener_conexion() as conn:
        usuario = (repositorio.buscar_por_id(conn, int(valor)) if valor.isdigit()
                   else repositorio.buscar_por_email(conn, valor))
    if usuario is None:
        raise ErrorOperacionInvalida("No existe el usuario %r." % valor)
    if not usuario.activo:
        raise ErrorOperacionInvalida("El usuario %r está desactivado." % valor)
    print("[DEBUG] Entrando como %s (id %s, %s) sin login." % (usuario.email, usuario.id_usuario, usuario.rol.value))
    return usuario
