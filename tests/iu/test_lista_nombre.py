"""Pruebas de la lista de Mercado: ordenar por la columna «Nombre»."""
import unittest
from unittest import mock

from simultradia.domain.entities.cotizacion_entity import PanelMercado
from simultradia.iu.mercado.lista_controller import ListaController
from tests.fakes import ServicioGenerico, VistaPanelFalsa, en_el_acto

_HILO = "simultradia.iu.base.panel_controller.ejecutar_en_hilo"


class PruebasOrdenarPorNombre(unittest.TestCase):
    def setUp(self):
        parche = mock.patch(_HILO, en_el_acto)
        parche.start()
        self.addCleanup(parche.stop)

    def test_el_nombre_se_ordena_de_la_a_a_la_z_y_pulsarlo_de_nuevo_lo_invierte(self):
        vista = VistaPanelFalsa()
        servicio = ServicioGenerico(obtener_panel=PanelMercado(items=[]))
        ListaController(vista, servicio, lambda _id: None)
        vista.acciones["al_ordenar"]("nombre")
        self.assertEqual(servicio.llamadas[-1][3:5], ("nombre", False))
        vista.acciones["al_ordenar"]("nombre")
        self.assertEqual(servicio.llamadas[-1][3:5], ("nombre", True))


if __name__ == "__main__":
    unittest.main()
