"""Manejo seguro de contraseñas.

Nunca se guarda la contraseña real: se guarda un "hash" (una huella) que no se
puede convertir de vuelta a la contraseña. Para comprobar un login se calcula
el hash de lo que escribió el usuario y se compara.
"""
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerificationError

_hasher = PasswordHasher()
_hash_de_relleno = None


def hashear_password(password: str) -> str:
    return _hasher.hash(password)


def verificar_password(password: str, hash_guardado: str) -> bool:
    try:
        return _hasher.verify(hash_guardado, password)
    except (VerificationError, InvalidHash):
        return False


def gastar_tiempo_de_verificacion(password: str) -> None:
    """Se usa cuando el email no existe, para tardar lo mismo que con un email
    válido. Así nadie puede descubrir qué emails están registrados midiendo
    cuánto demora la respuesta."""
    global _hash_de_relleno
    if _hash_de_relleno is None:
        _hash_de_relleno = _hasher.hash("contraseña-de-relleno")
    verificar_password(password, _hash_de_relleno)
