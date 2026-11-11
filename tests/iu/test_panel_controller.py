"""Pruebas de PanelController: un fallo que se repite en un refresco se avisa una sola vez."""
import unittest

from simultradia.core.exceptions import ErrorOperacionInvalida
from simultradia.iu.base.panel_controller import PanelController
from tests.fakes import VistaPanelFalsa


class PruebasAvisarUnaVez(unittest.TestCase):
    def setUp(self):
        self.vista = VistaPanelFalsa()
        self.controlador = PanelController(self.vista)
        self.error = ErrorOperacionInvalida("Base caída")

    def test_un_fallo_que_se_repite_se_avisa_una_sola_vez(self):
        for _ in range(3):
            self.controlador._avisar_una_vez("panel", self.error)
        self.assertEqual(self.vista.errores_mostrados, ["Base caída"])

    def test_si_se_recupera_y_vuelve_a_fallar_se_avisa_de_nuevo(self):
        self.controlador._avisar_una_vez("panel", self.error)
        self.controlador._recuperado("panel")
        self.controlador._avisar_una_vez("panel", self.error)
        self.assertEqual(len(self.vista.errores_mostrados), 2)

    def test_cada_consulta_lleva_su_propio_aviso(self):
        self.controlador._avisar_una_vez("velas", self.error)
        self.controlador._avisar_una_vez("consulta", self.error)
        self.assertEqual(len(self.vista.errores_mostrados), 2)


if __name__ == "__main__":
    unittest.main()
