"""Pruebas de la administración de usuarios."""
import unittest

from simultradia.core.exceptions import ErrorOperacionInvalida, ErrorPermisos
from simultradia.core.security import verificar_password
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.domain.enums import RolUsuario
from simultradia.services.usuario_admin_service import UsuarioAdminService
from tests.fakes import DatabaseFalsa, UsuarioRepoAdminFalso


class PruebasUsuarioAdminService(unittest.TestCase):
    def setUp(self):
        self.jefe = Usuario("Jefe", "j@x.com", "h", rol=RolUsuario.ADMIN, id_usuario=1)
        self.otro_admin = Usuario("Otro", "o@x.com", "h", rol=RolUsuario.ADMIN, id_usuario=2)
        self.ana = Usuario("Ana", "a@x.com", "h", id_usuario=3)
        self.repo = UsuarioRepoAdminFalso([self.jefe, self.otro_admin, self.ana])
        self.servicio = UsuarioAdminService(DatabaseFalsa(), self.repo)

    def test_listar_exige_administrador(self):
        self.assertEqual(len(self.servicio.listar(self.jefe)), 3)
        for actor in (self.ana, None):
            with self.assertRaises(ErrorPermisos):
                self.servicio.listar(actor)

    def test_desactivar_y_reactivar_un_usuario(self):
        self.servicio.cambiar_estado(self.jefe, 3, False)
        self.assertFalse(self.ana.activo)
        self.servicio.cambiar_estado(self.jefe, 3, True)
        self.assertTrue(self.ana.activo)

    def test_un_usuario_normal_no_puede_cambiar_estados(self):
        with self.assertRaises(ErrorPermisos):
            self.servicio.cambiar_estado(self.ana, 3, False)
        self.assertTrue(self.ana.activo)

    def test_no_puedes_desactivarte_a_ti_mismo(self):
        with self.assertRaises(ErrorOperacionInvalida):
            self.servicio.cambiar_estado(self.jefe, 1, False)
        self.assertTrue(self.jefe.activo)

    def test_no_se_puede_desactivar_a_otro_administrador(self):
        with self.assertRaises(ErrorOperacionInvalida):
            self.servicio.cambiar_estado(self.jefe, 2, False)
        self.assertTrue(self.otro_admin.activo)

    def test_usuario_inexistente(self):
        with self.assertRaises(ErrorOperacionInvalida):
            self.servicio.cambiar_estado(self.jefe, 99, False)


    # ------------------------------------------------------------ filtros
    def test_buscar_por_nombre_o_email_sin_importar_mayusculas(self):
        self.assertEqual([u.id_usuario for u in self.servicio.listar(self.jefe, texto=" ANA ")], [3])
        self.assertEqual([u.id_usuario for u in self.servicio.listar(self.jefe, texto="o@x")], [2])
        self.assertEqual(self.servicio.listar(self.jefe, texto="nadie"), [])

    def test_filtrar_por_rol_y_por_estado(self):
        self.ana.activo = False
        self.assertEqual([u.id_usuario for u in self.servicio.listar(self.jefe, rol="admin")], [1, 2])
        self.assertEqual([u.id_usuario for u in self.servicio.listar(self.jefe, rol="usuario")], [3])
        self.assertEqual([u.id_usuario for u in self.servicio.listar(self.jefe, activo=False)], [3])
        self.assertEqual([u.id_usuario for u in self.servicio.listar(self.jefe, activo=True)], [1, 2])

    def test_los_filtros_se_combinan(self):
        self.assertEqual([u.id_usuario for u in self.servicio.listar(self.jefe, texto="o", rol="admin", activo=True)], [1, 2])
        self.assertEqual(self.servicio.listar(self.jefe, texto="ana", rol="admin"), [])

    # ----------------------------------------------- contraseña temporal
    def test_restablecer_devuelve_una_temporal_y_guarda_solo_su_hash(self):
        temporal = self.servicio.restablecer_password(self.jefe, 3)
        self.assertEqual(len(temporal), 10)
        self.assertTrue(all(c in "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789" for c in temporal))
        self.assertNotEqual(self.ana.password_hash, temporal)          # nunca la contraseña en claro
        self.assertTrue(verificar_password(temporal, self.ana.password_hash))
        self.assertTrue(self.ana.debe_cambiar_password)

    def test_cada_restablecimiento_genera_una_contrasena_distinta(self):
        self.assertNotEqual(self.servicio.restablecer_password(self.jefe, 3),
                            self.servicio.restablecer_password(self.jefe, 3))

    def test_no_se_restablece_la_contrasena_de_un_administrador_ni_la_propia(self):
        for id_usuario in (1, 2):
            with self.assertRaises(ErrorOperacionInvalida):
                self.servicio.restablecer_password(self.jefe, id_usuario)
        self.assertEqual((self.jefe.password_hash, self.otro_admin.password_hash), ("h", "h"))

    def test_restablecer_a_un_usuario_inexistente(self):
        with self.assertRaises(ErrorOperacionInvalida):
            self.servicio.restablecer_password(self.jefe, 99)

    def test_restablecer_exige_administrador(self):
        for actor in (self.ana, None):
            with self.assertRaises(ErrorPermisos):
                self.servicio.restablecer_password(actor, 3)
        self.assertEqual(self.ana.password_hash, "h")
        self.assertFalse(self.ana.debe_cambiar_password)


if __name__ == "__main__":
    unittest.main()
