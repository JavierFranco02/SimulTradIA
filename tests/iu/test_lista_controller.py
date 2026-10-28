"""Pruebas del controlador de la lista de Mercado, con vista y servicio FALSOS."""
import unittest
from unittest import mock

from simultradia.core.exceptions import ErrorOperacionInvalida
from simultradia.domain.entities.activo_entity import Activo
from simultradia.domain.entities.cotizacion_entity import ActivoCotizado, PanelMercado
from simultradia.domain.enums import TipoActivo
from simultradia.iu.mercado.lista_controller import ListaController
from tests.fakes import EjecutorDiferido, ServicioGenerico, VistaPanelFalsa, en_el_acto

_HILO = "simultradia.iu.base.panel_controller.ejecutar_en_hilo"


def _panel(*ids):
    return PanelMercado(items=[ActivoCotizado(Activo("T%d" % i, "N", id_activo=i)) for i in ids])


class PruebasListaController(unittest.TestCase):
    def setUp(self):
        parche = mock.patch(_HILO, en_el_acto)
        parche.start()
        self.addCleanup(parche.stop)
        self.elegidos = []

    def _crear(self, panel=None, **vista_args):
        vista = VistaPanelFalsa(**vista_args)
        servicio = ServicioGenerico(obtener_panel=panel if panel is not None else _panel(7, 8))
        return vista, servicio, ListaController(vista, servicio, self.elegidos.append)

    def test_cargar_pide_la_lista_y_programa_el_refresco(self):
        vista, servicio, controlador = self._crear()
        controlador.cargar()
        self.assertEqual(servicio.llamadas, [("obtener_panel", "", "todos", "ticker", False, None)])
        self.assertEqual(vista.ultimo("panel")[1:], ("ticker", False))
        self.assertEqual([ms for ms, _ in vista.programadas], [3000])

    def test_al_terminar_la_primera_carga_elige_el_primer_activo_una_sola_vez(self):
        vista, _, controlador = self._crear()
        controlador.cargar()
        self.assertEqual(vista.eventos[-1], ("seleccionar", 7))
        vista.programadas[-1][1]()                                  # siguiente refresco
        self.assertEqual([e for e in vista.eventos if e[0] == "seleccionar"], [("seleccionar", 7)])

    def test_con_la_lista_vacia_no_elige_nada(self):
        vista, _, controlador = self._crear(panel=_panel())
        controlador.cargar()
        self.assertIsNone(vista.ultimo("seleccionar"))

    def test_buscar_envia_el_texto_y_la_categoria(self):
        vista, servicio, _ = self._crear(busqueda="sol", categoria=TipoActivo.CRIPTO)
        vista.acciones["al_filtrar"]()
        self.assertEqual(servicio.llamadas[-1], ("obtener_panel", "sol", "todos", "ticker", False, TipoActivo.CRIPTO))

    def test_cada_pestana_pide_su_filtro_y_orden(self):
        vista, servicio, _ = self._crear()
        esperado = {"ganadores": ("ganadores", "variacion", True), "perdedores": ("perdedores", "variacion", False),
                    "volumen": ("todos", "volumen", True), "todos": ("todos", "ticker", False)}
        for pestana, (filtro, orden, descendente) in esperado.items():
            vista.acciones["al_elegir_pestana"](pestana)
            self.assertEqual(servicio.llamadas[-1][2:5], (filtro, orden, descendente), pestana)

    def test_pulsar_el_mismo_encabezado_invierte_el_orden(self):
        vista, servicio, _ = self._crear()
        vista.acciones["al_ordenar"]("precio")
        self.assertEqual(servicio.llamadas[-1][3:5], ("precio", True))     # los números, de mayor a menor
        vista.acciones["al_ordenar"]("precio")
        self.assertEqual(servicio.llamadas[-1][3:5], ("precio", False))
        vista.acciones["al_ordenar"]("ticker")
        self.assertEqual(servicio.llamadas[-1][3:5], ("ticker", False))    # el nombre, de la A a la Z

    def test_elegir_un_activo_avisa_a_quien_muestra_el_grafico(self):
        vista, _, _ = self._crear()
        vista.acciones["al_elegir_activo"](5)
        self.assertEqual(self.elegidos, [5])

    def test_un_error_se_muestra_y_el_refresco_sigue(self):
        vista = VistaPanelFalsa()
        ListaController(vista, ServicioGenerico(obtener_panel=ErrorOperacionInvalida("Base caída")),
                        self.elegidos.append).cargar()
        self.assertEqual(vista.error, "Base caída")
        self.assertEqual(len(vista.programadas), 1)

    def test_si_la_pantalla_ya_no_existe_no_la_toca_ni_programa_mas(self):
        vista, _, controlador = self._crear()
        vista.viva = False
        controlador.cargar()
        self.assertEqual((vista.eventos, vista.programadas), ([], []))

    def test_una_respuesta_vieja_se_descarta(self):
        vista, servicio, controlador = self._crear(busqueda="a")
        ejecutor = EjecutorDiferido()
        with mock.patch(_HILO, ejecutor):
            controlador.cargar()                   # petición 1 (queda pendiente)
            vista.acciones["al_filtrar"]()         # petición 2
            ejecutor.terminar_todo()
        self.assertEqual(len([e for e in vista.eventos if e[0] == "panel"]), 1)   # solo la última llegó


if __name__ == "__main__":
    unittest.main()
