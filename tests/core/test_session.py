"""Pruebas de la sesión: cada instancia es independiente (ya no hay una global)."""
import unittest

from simultradia.core.session import Session
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.domain.enums import RolUsuario


def _usuario(rol=RolUsuario.USUARIO):
    return Usuario(nombre="Ana", email="ana@x.com", password_hash="h", rol=rol)


class PruebasSession(unittest.TestCase):
    def test_empieza_sin_sesion(self):
        sesion = Session()
        self.assertFalse(sesion.esta_iniciada)
        self.assertIsNone(sesion.usuario)
        self.assertFalse(sesion.es_admin)

    def test_iniciar_y_cerrar(self):
        sesion, ana = Session(), _usuario()
        sesion.iniciar(ana)
        self.assertTrue(sesion.esta_iniciada)
        self.assertIs(sesion.usuario, ana)
        sesion.cerrar()
        self.assertFalse(sesion.esta_iniciada)

    def test_es_admin_depende_del_rol(self):
        sesion = Session()
        sesion.iniciar(_usuario(RolUsuario.ADMIN))
        self.assertTrue(sesion.es_admin)
        sesion.iniciar(_usuario(RolUsuario.USUARIO))
        self.assertFalse(sesion.es_admin)

    def test_dos_sesiones_son_independientes(self):
        una, otra = Session(), Session()
        una.iniciar(_usuario())
        self.assertTrue(una.esta_iniciada)
        self.assertFalse(otra.esta_iniciada)


if __name__ == "__main__":
    unittest.main()
