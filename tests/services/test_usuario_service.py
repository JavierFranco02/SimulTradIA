"""Pruebas del servicio de usuarios. No necesitan PostgreSQL ni ventanas."""
import unittest
from decimal import Decimal

from simultradia.core.exceptions import (
    CredencialesInvalidas,
    CuentaDesactivada,
    DatosInvalidos,
    EmailYaRegistrado,
)
from simultradia.domain.enums import RolUsuario
from simultradia.services.usuario_service import UsuarioService
from tests.fakes import CuentaRepositorioFalso, DatabaseFalsa, RepositorioFalso

CLAVE = "Clave12345"


class PruebasUsuarioService(unittest.TestCase):
    def setUp(self):
        self.repo = RepositorioFalso()
        self.cuentas = CuentaRepositorioFalso()
        self.servicio = UsuarioService(DatabaseFalsa(), self.repo, self.cuentas)

    def _errores(self, funcion, *args):
        """Ejecuta y devuelve el diccionario de errores por campo de DatosInvalidos."""
        with self.assertRaises(DatosInvalidos) as contexto:
            funcion(*args)
        return contexto.exception.errores

    # ---------------------------------------------------------------- registro
    def test_registrar_crea_usuario_normal_con_hash(self):
        u = self.servicio.registrar("Ana Pérez", "  Ana@Correo.com ", CLAVE, CLAVE)
        self.assertEqual(u.email, "ana@correo.com")      # se normaliza
        self.assertEqual(u.rol, RolUsuario.USUARIO)
        self.assertNotEqual(u.password_hash, CLAVE)      # nunca la contraseña real
        self.assertIsNotNone(u.id_usuario)

    def test_registrar_crea_su_cuenta_simulada_con_el_capital_inicial(self):
        u = self.servicio.registrar("Ana", "ana@correo.com", CLAVE, CLAVE)
        self.assertEqual(len(self.cuentas.cuentas), 1)
        cuenta = self.cuentas.cuentas[0]
        self.assertEqual(cuenta.id_usuario, u.id_usuario)
        self.assertIsInstance(cuenta.capital_inicial, Decimal)
        self.assertGreater(cuenta.capital_inicial, 0)
        self.assertEqual(cuenta.saldo_disponible, cuenta.capital_inicial)

    def test_un_registro_rechazado_no_crea_cuenta(self):
        self._errores(self.servicio.registrar, "", "mal", "corta", "corta")
        self.assertEqual(self.cuentas.cuentas, [])
        self.servicio.registrar("Ana", "ana@correo.com", CLAVE, CLAVE)
        with self.assertRaises(EmailYaRegistrado):
            self.servicio.registrar("Otra", "ana@correo.com", CLAVE, CLAVE)
        self.assertEqual(len(self.cuentas.cuentas), 1)

    def test_email_duplicado_se_marca_en_el_campo_email(self):
        self.servicio.registrar("Ana", "ana@correo.com", CLAVE, CLAVE)
        with self.assertRaises(EmailYaRegistrado) as contexto:
            self.servicio.registrar("Otra Ana", "ANA@correo.com", CLAVE, CLAVE)
        self.assertEqual(list(contexto.exception.errores), ["email"])

    def test_cada_error_indica_su_campo(self):
        casos = [
            (("", "ana@correo.com", CLAVE, CLAVE), "nombre"),
            (("A", "ana@correo.com", CLAVE, CLAVE), "nombre"),
            (("Ana", "", CLAVE, CLAVE), "email"),
            (("Ana", "esto-no-es-un-email", CLAVE, CLAVE), "email"),
            (("Ana", "ana@correo.com", "", ""), "password"),
            (("Ana", "ana@correo.com", "corta", "corta"), "password"),
            (("Ana", "ana@correo.com", CLAVE, "otra-clave"), "confirmacion"),
        ]
        for datos, campo in casos:
            with self.subTest(datos=datos):
                self.assertEqual(list(self._errores(self.servicio.registrar, *datos)), [campo])

    def test_avisa_de_todos_los_campos_incorrectos_a_la_vez(self):
        errores = self._errores(self.servicio.registrar, "", "mal", "corta", "corta")
        self.assertEqual(sorted(errores), ["email", "nombre", "password"])

    def test_crear_administrador_asigna_rol_admin_y_no_crea_cuenta_simulada(self):
        u = self.servicio.crear_administrador("Jefe", "jefe@correo.com", CLAVE, CLAVE)
        self.assertEqual(u.rol, RolUsuario.ADMIN)
        self.assertEqual(self.cuentas.cuentas, [])

    # ------------------------------------------------------------------- login
    def test_autenticar_correcto_devuelve_el_usuario_y_guarda_ultimo_login(self):
        creado = self.servicio.registrar("Ana", "ana@correo.com", CLAVE, CLAVE)
        u = self.servicio.autenticar("ANA@correo.com", CLAVE)
        self.assertEqual(u.id_usuario, creado.id_usuario)
        self.assertEqual(self.repo.logins, [creado.id_usuario])

    def test_autenticar_con_contrasena_incorrecta(self):
        self.servicio.registrar("Ana", "ana@correo.com", CLAVE, CLAVE)
        with self.assertRaises(CredencialesInvalidas):
            self.servicio.autenticar("ana@correo.com", "otra-clave-1")
        self.assertEqual(self.repo.logins, [])

    def test_autenticar_con_email_inexistente(self):
        with self.assertRaises(CredencialesInvalidas):
            self.servicio.autenticar("nadie@correo.com", CLAVE)

    def test_autenticar_con_cuenta_desactivada(self):
        u = self.servicio.registrar("Ana", "ana@correo.com", CLAVE, CLAVE)
        u.activo = False
        with self.assertRaises(CuentaDesactivada):
            self.servicio.autenticar("ana@correo.com", CLAVE)
        self.assertEqual(self.repo.logins, [])

    def test_cuenta_desactivada_no_se_revela_con_contrasena_incorrecta(self):
        u = self.servicio.registrar("Ana", "ana@correo.com", CLAVE, CLAVE)
        u.activo = False
        with self.assertRaises(CredencialesInvalidas):
            self.servicio.autenticar("ana@correo.com", "otra-clave-1")

    def test_autenticar_con_campos_vacios_marca_cada_campo(self):
        self.assertEqual(sorted(self._errores(self.servicio.autenticar, "", "")),
                         ["email", "password"])
        self.assertEqual(list(self._errores(self.servicio.autenticar, "ana@correo.com", "")),
                         ["password"])

    def test_autenticar_valida_el_formato_del_email(self):
        errores = self._errores(self.servicio.autenticar, "esto-no-es-un-email", CLAVE)
        self.assertEqual(list(errores), ["email"])
        self.assertIn("válido", errores["email"])

    def test_autenticar_no_exige_el_largo_minimo_de_la_contrasena(self):
        # El largo mínimo es una regla para ELEGIR contraseña, no para entrar.
        with self.assertRaises(CredencialesInvalidas):
            self.servicio.autenticar("ana@correo.com", "corta")

    def test_un_usuario_con_contrasena_temporal_se_autentica_pero_queda_marcado(self):
        u = self.servicio.registrar("Ana", "ana@correo.com", CLAVE, CLAVE)
        self.assertFalse(u.debe_cambiar_password)
        u.debe_cambiar_password = True
        self.assertTrue(self.servicio.autenticar("ana@correo.com", CLAVE).debe_cambiar_password)

    # ------------------------------------------------- contraseña temporal
    def _con_temporal(self):
        u = self.servicio.registrar("Ana", "ana@correo.com", "Temporal123", "Temporal123")
        u.debe_cambiar_password = True
        return u

    def test_cambiar_la_contrasena_temporal(self):
        u = self._con_temporal()
        resultado = self.servicio.cambiar_password_temporal(" ANA@correo.com ", "Temporal123", "Nueva-Clave-9", "Nueva-Clave-9")
        self.assertFalse(resultado.debe_cambiar_password)
        self.assertFalse(u.debe_cambiar_password)
        self.assertNotEqual(u.password_hash, "Temporal123")
        self.servicio.autenticar("ana@correo.com", "Nueva-Clave-9")          # la nueva funciona
        with self.assertRaises(CredencialesInvalidas):
            self.servicio.autenticar("ana@correo.com", "Temporal123")        # la temporal ya no

    def test_cada_error_del_cambio_indica_su_campo(self):
        self._con_temporal()
        casos = [
            (("", "Nueva-Clave-9", "Nueva-Clave-9"), "actual"),
            (("Temporal123", "corta", "corta"), "password"),
            (("Temporal123", "Nueva-Clave-9", "otra-cosa"), "confirmacion"),
            (("Temporal123", "Temporal123", "Temporal123"), "password"),     # igual a la temporal
        ]
        for datos, campo in casos:
            with self.subTest(datos=datos):
                errores = self._errores(self.servicio.cambiar_password_temporal, "ana@correo.com", *datos)
                self.assertEqual(list(errores), [campo])

    def test_con_la_temporal_equivocada_o_un_email_inexistente_es_credenciales_invalidas(self):
        self._con_temporal()
        with self.assertRaises(CredencialesInvalidas):
            self.servicio.cambiar_password_temporal("ana@correo.com", "no-es-esa-1", "Nueva-Clave-9", "Nueva-Clave-9")
        with self.assertRaises(CredencialesInvalidas):
            self.servicio.cambiar_password_temporal("nadie@correo.com", "Temporal123", "Nueva-Clave-9", "Nueva-Clave-9")

    def test_solo_funciona_si_hay_un_cambio_pendiente(self):
        u = self.servicio.registrar("Ana", "ana@correo.com", CLAVE, CLAVE)      # contraseña normal
        with self.assertRaises(CredencialesInvalidas):
            self.servicio.cambiar_password_temporal("ana@correo.com", CLAVE, "Nueva-Clave-9", "Nueva-Clave-9")
        self.servicio.autenticar("ana@correo.com", CLAVE)                       # la contraseña no cambió

    def test_una_cuenta_desactivada_no_puede_cambiarla(self):
        u = self._con_temporal()
        u.activo = False
        with self.assertRaises(CuentaDesactivada):
            self.servicio.cambiar_password_temporal("ana@correo.com", "Temporal123", "Nueva-Clave-9", "Nueva-Clave-9")


if __name__ == "__main__":
    unittest.main()
