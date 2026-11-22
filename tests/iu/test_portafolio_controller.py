"""Pruebas del controlador de Portafolio, con vista y servicio FALSOS."""
import unittest
from unittest import mock

from simultradia.core.exceptions import ErrorOperacionInvalida
from simultradia.core.session import Session
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.iu.portafolio.portafolio_controller import PortafolioController
from tests.fakes import EjecutorDiferido, ServicioGenerico, VistaPanelFalsa, en_el_acto

_HILO = "simultradia.iu.base.panel_controller.ejecutar_en_hilo"


class _VistaPortafolio(VistaPanelFalsa):
    def mostrar_portafolio(self, resumen): self.eventos.append(("portafolio", resumen))


class PruebasPortafolioController(unittest.TestCase):
    def setUp(self):
        parche = mock.patch(_HILO, en_el_acto)
        parche.start()
        self.addCleanup(parche.stop)
        self.session = Session()
        self.ana = Usuario("Ana", "a@x.com", "h", id_usuario=2)
        self.session.iniciar(self.ana)

    def _crear(self, resumen="RESUMEN"):
        vista = _VistaPortafolio()
        servicio = ServicioGenerico(obtener_portafolio=resumen)
        return vista, servicio, PortafolioController(vista, servicio, self.session)

    def test_cargar_pide_el_resumen_con_el_usuario_y_lo_muestra(self):
        vista, servicio, controlador = self._crear()
        controlador.cargar()
        self.assertEqual(servicio.llamadas, [("obtener_portafolio", self.ana)])
        self.assertEqual(vista.ultimo("portafolio"), "RESUMEN")

    def test_programa_el_refresco_cada_15_segundos(self):
        vista, servicio, controlador = self._crear()
        controlador.cargar()
        self.assertEqual([ms for ms, _ in vista.programadas], [15000])
        vista.programadas[-1][1]()
        self.assertEqual(len(servicio.llamadas), 2)

    def test_si_la_consulta_anterior_no_termino_no_lanza_otra(self):
        vista, servicio, controlador = self._crear()
        ejecutor = EjecutorDiferido()
        with mock.patch(_HILO, ejecutor):
            controlador.cargar()
            vista.programadas[-1][1]()
            self.assertEqual(len(ejecutor.pendientes), 1)
            ejecutor.terminar_todo()
            vista.programadas[-1][1]()
            self.assertEqual(len(ejecutor.pendientes), 1)       # ya terminó la anterior: pide la siguiente
        self.assertEqual(len([e for e in vista.eventos if e[0] == "portafolio"]), 1)

    def test_un_fallo_que_se_repite_se_avisa_una_sola_vez_y_el_refresco_sigue(self):
        vista, _, controlador = self._crear(ErrorOperacionInvalida("Base caída"))
        controlador.cargar()
        for _ in range(3):
            vista.programadas[-1][1]()
        self.assertEqual(vista.errores_mostrados, ["Base caída"])
        self.assertEqual(len(vista.programadas), 4)

    def test_si_se_recupera_y_vuelve_a_fallar_se_avisa_de_nuevo(self):
        vista = _VistaPortafolio()
        servicio = ServicioGenerico(obtener_portafolio=ErrorOperacionInvalida("Base caída"))
        controlador = PortafolioController(vista, servicio, self.session)
        controlador.cargar()
        servicio._respuestas["obtener_portafolio"] = "RESUMEN"
        vista.programadas[-1][1]()
        servicio._respuestas["obtener_portafolio"] = ErrorOperacionInvalida("Base caída")
        vista.programadas[-1][1]()
        self.assertEqual(len(vista.errores_mostrados), 2)

    def test_si_la_pantalla_ya_no_existe_no_la_toca_ni_programa_mas(self):
        vista, servicio, controlador = self._crear()
        vista.viva = False
        controlador.cargar()
        self.assertEqual((servicio.llamadas, vista.eventos, vista.programadas), ([], [], []))


if __name__ == "__main__":
    unittest.main()
