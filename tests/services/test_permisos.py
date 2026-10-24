"""Pruebas del control de permisos."""
import unittest

from simultradia.core.exceptions import ErrorPermisos
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.domain.enums import RolUsuario
from simultradia.services.permisos import exigir_admin


def _usuario(rol):
    return Usuario(nombre="Ana", email="ana@x.com", password_hash="h", rol=rol)


class PruebasPermisos(unittest.TestCase):
    def test_el_administrador_pasa(self):
        exigir_admin(_usuario(RolUsuario.ADMIN))

    def test_un_usuario_normal_es_rechazado(self):
        with self.assertRaises(ErrorPermisos):
            exigir_admin(_usuario(RolUsuario.USUARIO))

    def test_sin_usuario_es_rechazado(self):
        with self.assertRaises(ErrorPermisos):
            exigir_admin(None)


if __name__ == "__main__":
    unittest.main()
