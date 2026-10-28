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
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.iu.auth.cambiar_password_controller import CambiarPasswordController
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


def _usuario(temporal=False):
    return Usuario(nombre="Ana", email="ana@x.com", password_hash="h", debe_cambiar_password=temporal)


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
        usuario = _usuario()
        vista, servicio = VistaFalsa(), ServicioFalso(resultado=usuario)
        LoginController(vista, servicio, self.nav, self.session).iniciar_sesion()
        self.assertEqual(servicio.llamadas, [("autenticar", "ana@x.com", "Clave12345")])
        self.assertEqual(self.nav.llamadas, [("home", {})])
        self.assertTrue(vista.ocupado)   # el botón queda ocupado hasta que cambia la pantalla
        self.assertIs(self.session.usuario, usuario)   # el controlador abrió la sesión

    def test_login_con_contrasena_temporal_va_a_cambiarla_y_no_abre_la_sesion(self):
        vista, servicio = VistaFalsa(), ServicioFalso(resultado=_usuario(temporal=True))
        LoginController(vista, servicio, self.nav, self.session).iniciar_sesion()
        self.assertEqual(self.nav.llamadas, [("cambiar_password", {"email": "ana@x.com"})])
        self.assertFalse(self.session.esta_iniciada)

    def test_limpia_los_errores_anteriores_al_enviar(self):
        vista = VistaFalsa()
        LoginController(vista, ServicioFalso(resultado=_usuario()), self.nav, self.session).iniciar_sesion()
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
        vista, servicio = VistaFalsa(), ServicioFalso(resultado=_usuario())
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

    # ------------------------------------------- cambio de contraseña temporal
    def test_al_cambiarla_vuelve_al_login_con_un_aviso(self):
        vista = VistaFalsa()
        CambiarPasswordController(vista, _ServicioCambio(_usuario()), self.nav, "ana@x.com").guardar()
        nombre, parametros = self.nav.llamadas[0]
        self.assertEqual((nombre, parametros["email"]), ("login", "ana@x.com"))
        self.assertIn("Contraseña actualizada", parametros["mensaje"])
        self.assertFalse(self.session.esta_iniciada)

    def test_el_servicio_recibe_el_email_de_la_cuenta_y_lo_escrito(self):
        vista, servicio = VistaFalsa(actual="Temporal1", password="Nueva-Clave-9", confirmacion="Nueva-Clave-9"), _ServicioCambio(_usuario())
        CambiarPasswordController(vista, servicio, self.nav, "ana@x.com").guardar()
        self.assertEqual(servicio.llamadas, [("ana@x.com", "Temporal1", "Nueva-Clave-9", "Nueva-Clave-9")])

    def test_temporal_equivocada_es_error_general_y_borra_ese_campo(self):
        vista = VistaFalsa()
        CambiarPasswordController(vista, _ServicioCambio(error=CredencialesInvalidas()), self.nav, "ana@x.com").guardar()
        self.assertEqual(vista.error_general, "Email o contraseña incorrectos.")
        self.assertEqual(vista.campos_limpiados, ["actual"])
        self.assertEqual(self.nav.llamadas, [])

    def test_errores_de_campo_del_cambio_van_cada_uno_a_su_campo(self):
        vista = VistaFalsa()
        error = DatosInvalidos({"password": "La contraseña debe tener al menos 8 caracteres."})
        CambiarPasswordController(vista, _ServicioCambio(error=error), self.nav, "ana@x.com").guardar()
        self.assertEqual(vista.errores_campos, error.errores)
        self.assertFalse(vista.ocupado)

    def test_se_puede_volver_al_login_sin_cambiarla(self):
        vista = VistaFalsa()
        CambiarPasswordController(vista, ServicioFalso(), self.nav, "ana@x.com")
        vista.acciones["al_volver_a_login"]()
        self.assertEqual(self.nav.llamadas, [("login", {})])

    # ------------------------------- el usuario se va mientras la operación sigue
    def test_login_que_termina_despues_de_salir_no_navega_ni_abre_la_sesion(self):
        vista, servicio, ejecutor = VistaFalsa(), ServicioFalso(resultado=_usuario()), EjecutorDiferido()
        with mock.patch(_EJECUTAR_EN_HILO, ejecutor):
            LoginController(vista, servicio, self.nav, self.session).iniciar_sesion()
            vista.viva = False            # el usuario pasa a otra pantalla mientras espera
            ejecutor.terminar_todo()
        self.assertEqual(self.nav.llamadas, [])
        self.assertFalse(self.session.esta_iniciada)   # nunca se abrió: no hay nada que deshacer

    def test_login_que_termina_con_la_pantalla_viva_abre_la_sesion_y_navega(self):
        vista, servicio, ejecutor = VistaFalsa(), ServicioFalso(resultado=_usuario()), EjecutorDiferido()
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


class _ServicioCambio:
    """Servicio falso para el cambio de contraseña temporal: anota lo que recibe."""

    def __init__(self, resultado=None, error=None):
        self.resultado, self.error, self.llamadas = resultado, error, []

    def cambiar_password_temporal(self, email, actual, nueva, confirmacion):
        self.llamadas.append((email, actual, nueva, confirmacion))
        if self.error:
            raise self.error
        return self.resultado


if __name__ == "__main__":
    unittest.main()
