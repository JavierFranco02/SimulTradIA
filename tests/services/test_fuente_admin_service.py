"""Pruebas de la administración de fuentes de datos."""
import unittest

from simultradia.core.exceptions import ErrorOperacionInvalida, ErrorPermisos
from simultradia.domain.entities.fuente_entity import Fuente
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.domain.enums import RolUsuario
from simultradia.services.fuente_admin_service import FuenteAdminService
from tests.fakes import DatabaseFalsa, RepoFuenteFalso

ADMIN = Usuario("Jefe", "j@x.com", "h", rol=RolUsuario.ADMIN, id_usuario=1)
NORMAL = Usuario("Ana", "a@x.com", "h", id_usuario=2)


class PruebasFuenteAdminService(unittest.TestCase):
    def setUp(self):
        self.repo = RepoFuenteFalso([Fuente("Binance", id_fuente=1), Fuente("Yahoo Finance", id_fuente=2)])
        self.servicio = FuenteAdminService(DatabaseFalsa(), self.repo)

    def test_listar(self):
        self.assertEqual([f.nombre for f in self.servicio.listar(ADMIN)], ["Binance", "Yahoo Finance"])

    def test_deshabilitar_y_habilitar_una_fuente(self):
        self.servicio.cambiar_estado(ADMIN, 2, False)
        self.assertFalse(self.repo.fuentes[1].activa)
        self.servicio.cambiar_estado(ADMIN, 2, True)
        self.assertTrue(self.repo.fuentes[1].activa)

    def test_una_fuente_inexistente(self):
        with self.assertRaises(ErrorOperacionInvalida):
            self.servicio.cambiar_estado(ADMIN, 99, False)

    def test_todo_exige_administrador(self):
        for actor in (NORMAL, None):
            with self.assertRaises(ErrorPermisos):
                self.servicio.listar(actor)
            with self.assertRaises(ErrorPermisos):
                self.servicio.cambiar_estado(actor, 1, False)
        self.assertTrue(self.repo.fuentes[0].activa)


if __name__ == "__main__":
    unittest.main()
