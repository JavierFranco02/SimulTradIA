"""Pruebas del Navegador con ventana y pantallas FALSAS (sin tkinter)."""
import unittest

from simultradia.iu.navegacion import Navegador
from tests.fakes import PantallaFalsa, ShellFalso, VentanaFalsa


class PruebasNavegador(unittest.TestCase):
    def setUp(self):
        self.ventana = VentanaFalsa()
        self.nav = Navegador(self.ventana, servicios="SERVICIOS", session="SESION")
        self.creadas = []
        self.nav.registrar("login", self._fabrica(PantallaFalsa), tamano=(480, 660), minimo=(420, 600))
        self.nav.registrar("registro", self._fabrica(PantallaFalsa), tamano=(480, 660), minimo=(420, 600))
        self.nav.registrar("home", self._fabrica(ShellFalso), tamano=(1100, 700),
                           minimo=(900, 600), seccion_inicial="inicio")
        self.nav.registrar("inicio", self._fabrica(PantallaFalsa), en_shell=True)
        self.nav.registrar("mercado", self._fabrica(PantallaFalsa), en_shell=True)

    def _fabrica(self, clase):
        def fabrica(padre, nav, **parametros):
            vista = clase(padre, **parametros)
            self.creadas.append(vista)
            return vista
        return fabrica

    def test_expone_servicios_y_sesion_a_las_fabricas(self):
        self.assertEqual((self.nav.servicios, self.nav.session), ("SERVICIOS", "SESION"))

    def test_muestra_la_pantalla_con_sus_parametros(self):
        self.nav.ir_a("login", email="ana@x.com")
        vista = self.creadas[0]
        self.assertIs(vista.padre, self.ventana)
        self.assertEqual(vista.parametros, {"email": "ana@x.com"})
        self.assertTrue(vista.empaquetada)

    def test_cambiar_de_pantalla_destruye_la_anterior(self):
        self.nav.ir_a("login")
        self.nav.ir_a("registro")
        self.assertTrue(self.creadas[0].destruida)
        self.assertFalse(self.creadas[1].destruida)

    def test_home_abre_la_seccion_inicial_dentro_del_shell(self):
        self.nav.ir_a("home")
        shell, seccion = self.creadas
        self.assertIs(seccion.padre, shell.contenido)
        self.assertEqual(shell.secciones_marcadas, ["inicio"])

    def test_cambiar_de_seccion_destruye_solo_la_seccion_anterior(self):
        self.nav.ir_a("home")
        shell, inicio = self.creadas
        self.nav.ir_a("mercado", id_activo=5)
        mercado = self.creadas[2]
        self.assertTrue(inicio.destruida)
        self.assertFalse(shell.destruida)
        self.assertIs(mercado.padre, shell.contenido)
        self.assertEqual(mercado.parametros, {"id_activo": 5})
        self.assertEqual(shell.secciones_marcadas, ["inicio", "mercado"])

    def test_una_seccion_sin_shell_falla(self):
        with self.assertRaises(RuntimeError):
            self.nav.ir_a("inicio")

    def test_salir_del_shell_lo_destruye_y_ya_no_hay_secciones(self):
        self.nav.ir_a("home")
        self.nav.ir_a("login")
        self.assertTrue(self.creadas[0].destruida)     # el shell
        with self.assertRaises(RuntimeError):
            self.nav.ir_a("mercado")

    def test_pantalla_inexistente(self):
        with self.assertRaises(KeyError):
            self.nav.ir_a("no_existe")

    def test_no_se_puede_registrar_dos_veces_el_mismo_nombre(self):
        with self.assertRaises(ValueError):
            self.nav.registrar("login", self._fabrica(PantallaFalsa))

    def test_la_ventana_solo_se_redimensiona_si_cambia_el_tamano(self):
        self.nav.ir_a("login")
        self.nav.ir_a("registro")                      # mismo tamaño: no se mueve
        self.assertEqual(self.ventana.geometrias, ["480x660"])
        self.assertEqual(self.ventana.centrados, 1)
        self.nav.ir_a("home")
        self.assertEqual(self.ventana.geometrias, ["480x660", "1100x700"])
        self.assertEqual(self.ventana.centrados, 2)
        self.assertEqual(self.ventana.minimos[-1], (900, 600))
        self.nav.ir_a("login")
        self.assertEqual(self.ventana.geometrias[-1], "480x660")
        self.assertEqual(self.ventana.minimos[-1], (420, 600))


if __name__ == "__main__":
    unittest.main()
