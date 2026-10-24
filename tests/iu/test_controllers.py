"""Pruebas de los controladores con una vista, un servicio y un navegador FALSOS.

No hace falta abrir ventanas: el controlador solo habla con objetos que tengan
los métodos esperados.
"""
import unittest
from unittest import mock

from simultradia.core.exceptions import (
    CredencialesInvalidas,
    DatosInvalidos,
    EmailYaRegistrado,
)
from simultradia.core.session import Session
from simultradia.iu.auth.login_controller import LoginController
from simultradia.iu.auth.registro_controller import RegistroController
from simultradia.iu.shell.shell_controller import ShellController
from tests.fakes import (
    EjecutorDiferido,
    NavegadorFalso,
    ServicioFalso,
    VistaFalsa,
    en_el_acto,
)

# Los dos formularios comparten FormController: ahí está ejecutar_en_hilo.
_EJECUTAR_EN_HILO = "simultradia.iu.base.form_controller.ejecutar_en_hilo"


class PruebasControladores(unittest.TestCase):
    def setUp(self):
        parche = mock.patch(_EJECUTAR_EN_HILO, en_el_acto)
        parche.start()
        self.addCleanup(parche.stop)
        self.nav = NavegadorFalso()
        self.session = Session()

    # ------------------------------------------------------------------- login
    def test_se_engancha_a_la_vista(self):
        vista = VistaFalsa()
        LoginController(vista, ServicioFalso(), self.nav, self.session)
        self.assertIn("al_iniciar_sesion", vista.acciones)
        vista.acciones["al_ir_a_registro"]()
        self.assertEqual(self.nav.llamadas, [("registro", {})])

    def test_login_correcto_abre_la_sesion_y_navega_al_home(self):
        vista, servicio = VistaFalsa(), ServicioFalso(resultado="USUARIO")
        LoginController(vista, servicio, self.nav, self.session).iniciar_sesion()
        self.assertEqual(servicio.llamadas, [("autenticar", "ana@x.com", "Clave12345")])
        self.assertEqual(self.nav.llamadas, [("home", {})])
        self.assertTrue(vista.ocupado)   # el botón queda ocupado hasta que cambia la pantalla
        self.assertEqual(self.session.usuario, "USUARIO")   # el controlador abrió la sesión

    def test_limpia_los_errores_anteriores_al_enviar(self):
        vista = VistaFalsa()
        LoginController(vista, ServicioFalso(resultado="U"), self.nav, self.session).iniciar_sesion()
        self.assertEqual(vista.errores_limpiados, 1)

    def test_errores_de_campo_van_cada_uno_a_su_campo(self):
        vista = VistaFalsa()
        error = DatosInvalidos({"email": "Ingresa tu email.", "password": "Ingresa tu contraseña."})
        LoginController(vista, ServicioFalso(error=error), self.nav, self.session).iniciar_sesion()
        self.assertEqual(vista.errores_campos, error.errores)
        self.assertIsNone(vista.error_general)
        self.assertFalse(vista.ocupado)
        self.assertEqual(vista.campos_limpiados, [])      # no borra la contraseña

    def test_credenciales_incorrectas_es_error_general_y_borra_la_contrasena(self):
        vista = VistaFalsa()
        LoginController(vista, ServicioFalso(error=CredencialesInvalidas()), self.nav, self.session).iniciar_sesion()
        self.assertEqual(vista.error_general, "Email o contraseña incorrectos.")
        self.assertEqual(vista.errores_campos, {})
        self.assertEqual(vista.campos_limpiados, ["password"])
        self.assertFalse(vista.ocupado)
        self.assertFalse(self.session.esta_iniciada)

    def test_error_inesperado_no_revela_detalles(self):
        vista = VistaFalsa()
        servicio = ServicioFalso(error=RuntimeError("detalle interno secreto"))
        with self.assertLogs("simultradia.iu.base.form_controller", level="ERROR"):
            LoginController(vista, servicio, self.nav, self.session).iniciar_sesion()
        self.assertNotIn("secreto", vista.error_general)

    def test_si_la_vista_ya_no_existe_no_la_toca(self):
        vista = VistaFalsa()
        vista.viva = False
        LoginController(vista, ServicioFalso(error=CredencialesInvalidas()), self.nav, self.session).iniciar_sesion()
        self.assertIsNone(vista.error_general)
        self.assertEqual(vista.campos_limpiados, [])

    def test_ignora_pulsaciones_mientras_esta_ocupado(self):
        vista, servicio = VistaFalsa(), ServicioFalso(resultado="U")
        vista.ocupado = True
        LoginController(vista, servicio, self.nav, self.session).iniciar_sesion()
        self.assertEqual(servicio.llamadas, [])

    # ---------------------------------------------------------------- registro
    def test_registro_envia_tambien_la_confirmacion_al_servicio(self):
        class Creado: email = "ana@x.com"
        vista, servicio = VistaFalsa(confirmacion="otra"), ServicioFalso(resultado=Creado())
        RegistroController(vista, servicio, self.nav).registrar()
        self.assertEqual(servicio.llamadas,
                         [("registrar", "Ana", "ana@x.com", "Clave12345", "otra")])

    def test_registro_correcto_vuelve_al_login_con_el_email(self):
        class Creado: email = "ana@x.com"
        vista, servicio = VistaFalsa(), ServicioFalso(resultado=Creado())
        RegistroController(vista, servicio, self.nav).registrar()
        nombre, parametros = self.nav.llamadas[0]
        self.assertEqual(nombre, "login")
        self.assertEqual(parametros["email"], "ana@x.com")
        self.assertIn("Cuenta creada", parametros["mensaje"])

    def test_registro_email_duplicado_se_muestra_en_el_campo_email(self):
        vista = VistaFalsa()
        RegistroController(vista, ServicioFalso(error=EmailYaRegistrado()), self.nav).registrar()
        self.assertEqual(list(vista.errores_campos), ["email"])

    def test_registro_puede_volver_al_login(self):
        vista = VistaFalsa()
        RegistroController(vista, ServicioFalso(), self.nav)
        vista.acciones["al_volver_a_login"]()
        self.assertEqual(self.nav.llamadas, [("login", {})])

    # ------------------------------- el usuario se va mientras la operación sigue
    def test_login_que_termina_despues_de_salir_no_navega_ni_abre_la_sesion(self):
        vista, servicio, ejecutor = VistaFalsa(), ServicioFalso(resultado="USUARIO"), EjecutorDiferido()
        with mock.patch(_EJECUTAR_EN_HILO, ejecutor):
            LoginController(vista, servicio, self.nav, self.session).iniciar_sesion()
            vista.viva = False            # el usuario pasa a otra pantalla mientras espera
            ejecutor.terminar_todo()
        self.assertEqual(self.nav.llamadas, [])
        self.assertFalse(self.session.esta_iniciada)   # nunca se abrió: no hay nada que deshacer

    def test_login_que_termina_con_la_pantalla_viva_abre_la_sesion_y_navega(self):
        vista, servicio, ejecutor = VistaFalsa(), ServicioFalso(resultado="USUARIO"), EjecutorDiferido()
        with mock.patch(_EJECUTAR_EN_HILO, ejecutor):
            LoginController(vista, servicio, self.nav, self.session).iniciar_sesion()
            ejecutor.terminar_todo()
        self.assertEqual(self.nav.llamadas, [("home", {})])
        self.assertTrue(self.session.esta_iniciada)

    def test_registro_que_termina_despues_de_salir_no_vuelve_al_login(self):
        class Creado: email = "ana@x.com"
        vista, servicio, ejecutor = VistaFalsa(), ServicioFalso(resultado=Creado()), EjecutorDiferido()
        with mock.patch(_EJECUTAR_EN_HILO, ejecutor):
            RegistroController(vista, servicio, self.nav).registrar()
            vista.viva = False
            ejecutor.terminar_todo()
        self.assertEqual(self.nav.llamadas, [])

    # ------------------------------------------------------------------- shell
    def test_el_menu_del_shell_cambia_de_seccion(self):
        vista = VistaFalsa()
        ShellController(vista, self.session, self.nav)
        vista.acciones["al_elegir_seccion"]("inicio")
        self.assertEqual(self.nav.llamadas, [("inicio", {})])

    def test_cerrar_sesion_la_cierra_y_vuelve_al_login(self):
        vista = VistaFalsa()
        self.session.iniciar("USUARIO")
        ShellController(vista, self.session, self.nav)
        vista.acciones["al_cerrar_sesion"]()
        self.assertFalse(self.session.esta_iniciada)
        self.assertEqual(self.nav.llamadas, [("login", {})])


if __name__ == "__main__":
    unittest.main()
