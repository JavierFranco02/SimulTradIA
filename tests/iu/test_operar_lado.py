"""Pruebas de Operar: el patrimonio de la cabecera y la cantidad al cambiar entre Comprar y Vender."""
import unittest
from decimal import Decimal as D
from types import SimpleNamespace
from unittest import mock

from simultradia.core.session import Session
from simultradia.domain.entities.cotizacion_entity import PanelMercado
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.domain.enums import LadoOrden
from simultradia.iu.operar.operar_controller import OperarController
from tests.fakes import ServicioGenerico, en_el_acto
from tests.iu.test_operar_controller import _HILO, _VistaOperar, _estado


class PruebasOperarLado(unittest.TestCase):
    def setUp(self):
        parche = mock.patch(_HILO, en_el_acto)
        parche.start()
        self.addCleanup(parche.stop)
        self.session = Session()
        self.session.iniciar(Usuario("Ana", "a@x.com", "h", id_usuario=2))

    def _cargar(self, lado, posicion):
        vista = _VistaOperar(lado=lado)
        operar = ServicioGenerico(obtener_estado=_estado(SimpleNamespace(posicion=posicion)), estimar="EST")
        mercado = ServicioGenerico(obtener_panel=PanelMercado(items=["A"]))
        OperarController(vista, operar, mercado, self.session, lambda _id: None).cargar()
        return vista

    def test_el_patrimonio_llega_a_la_cabecera(self):
        vista = self._cargar(LadoOrden.COMPRA, None)
        self.assertEqual(vista.ultimo("patrimonio"), D("10000"))

    def test_al_pasar_a_vender_se_propone_la_posicion_entera(self):
        vista = self._cargar(LadoOrden.VENTA, SimpleNamespace(cantidad=D("2")))
        vista.acciones["al_cambiar_lado"]()
        self.assertEqual(vista.ultimo("cantidad"), D("2"))

    def test_al_pasar_a_vender_sin_posicion_la_caja_queda_vacia(self):
        vista = self._cargar(LadoOrden.VENTA, None)
        vista.acciones["al_cambiar_lado"]()
        self.assertIsNotNone(vista.ultimo("limpiar_cantidad"))
        self.assertIsNone(vista.ultimo("cantidad"))

    def test_al_volver_a_comprar_la_caja_se_vacia(self):
        vista = self._cargar(LadoOrden.COMPRA, SimpleNamespace(cantidad=D("2")))
        vista.acciones["al_cambiar_lado"]()
        self.assertIsNotNone(vista.ultimo("limpiar_cantidad"))
        self.assertIsNone(vista.ultimo("cantidad"))


if __name__ == "__main__":
    unittest.main()
