"""Errores propios de la aplicación.

Todos heredan de ErrorAplicacion: son errores "esperados" cuyo mensaje se puede
mostrar tal cual al usuario. Cualquier otra excepción es un error inesperado.
"""
from typing import Dict


class ErrorAplicacion(Exception):
    """Base de los errores cuyo mensaje es seguro mostrar al usuario."""


class ErrorBaseDatos(ErrorAplicacion):
    """No se pudo hablar con PostgreSQL."""


class ErrorServicioExterno(ErrorAplicacion):
    """No se pudo hablar con una API de afuera (Binance...)."""


class ErrorOperacionInvalida(ErrorAplicacion):
    """La acción pedida no se puede hacer (por ejemplo, desactivarse a uno mismo)."""


class ErrorPermisos(ErrorAplicacion):
    """Quien pide la acción no tiene permiso para hacerla (por ejemplo, no es administrador)."""

    def __init__(self, mensaje: str = "No tienes permisos para realizar esta acción."):
        super().__init__(mensaje)


class DatosInvalidos(ErrorAplicacion):
    """Uno o más campos del formulario no cumplen las reglas.

    `errores` dice qué campo falló y por qué, para que la pantalla ponga cada
    mensaje debajo de su campo:

        DatosInvalidos({"email": "Ingresa un email válido.", "password": "Muy corta."})
    """

    def __init__(self, errores: Dict[str, str]):
        self.errores = errores
        super().__init__(" ".join(errores.values()))


class EmailYaRegistrado(DatosInvalidos):
    def __init__(self):
        super().__init__({"email": "Ya existe una cuenta con ese email."})


class CredencialesInvalidas(ErrorAplicacion):
    def __init__(self, mensaje: str = "Email o contraseña incorrectos."):
        super().__init__(mensaje)


class CuentaDesactivada(ErrorAplicacion):
    def __init__(self, mensaje: str = "Tu cuenta está desactivada. Contacta al administrador."):
        super().__init__(mensaje)
