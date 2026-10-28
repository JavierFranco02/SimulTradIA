"""Pruebas del controlador del gráfico de Mercado, con vista y servicios FALSOS."""
import unittest
from datetime import datetime, timezone
from decimal import Decimal as D
from unittest import mock

from simultradia.core.exceptions import ErrorOperacionInvalida
from simultradia.domain.entities.activo_entity import Activo
from simultradia.domain.entities.cotizacion_entity import ActivoCotizado, Cotizacion
from simultradia.domain.enums import IntervaloVela as I
from simultradia.domain.enums import TipoActivo
from simultradia.iu.mercado.grafico_controller import GraficoController
from tests.fakes import EjecutorDiferido, ServicioGenerico, VistaPanelFalsa, en_el_acto

_HILO = "simultradia.iu.base.panel_controller.ejecutar_en_hilo"


def _item(id_activo=1, precio="100", tipo=TipoActivo.CRIPTO):
    return ActivoCotizado(Activo("T%d" % id_activo, "Nombre", tipo=tipo, id_activo=id_activo),
                          Cotizacion(precio=D(precio), id_activo=id_activo, actualizado_en=datetime.now(timezone.utc)))


class PruebasGraficoController(unittest.TestCase):
    def setUp(self):
        parche = mock.patch(_HILO, en_el_acto)
        parche.start()
        self.addCleanup(parche.stop)

    def _crear(self, activo=None):
        vista = VistaPanelFalsa()
        mercado = ServicioGenerico(obtener_activo=activo or _item())
        grafico = ServicioGenerico(obtener_datos="DATOS", con_precio="DATOS_EN_VIVO")
        return vista, mercado, grafico, GraficoController(vista, mercado, grafico)

    def _graficos(self, vista):
        return [e for e in vista.eventos if e[0] == "grafico"]

    def test_sin_activo_elegido_no_pide_nada_pero_sigue_programando(self):
        vista, mercado, grafico, controlador = self._crear()
        controlador.cargar()
        self.assertEqual((mercado.llamadas, grafico.llamadas), ([], []))
        self.assertEqual([ms for ms, _ in vista.programadas], [2000])

    def test_elegir_un_activo_limpia_el_grafico_y_muestra_su_ficha_y_sus_velas(self):
        vista, mercado, grafico, controlador = self._crear()
        controlador.cargar()
        controlador.mostrar_activo(1)
        self.assertEqual(vista.eventos[0], ("limpiar_grafico", ()))
        self.assertEqual(vista.ultimo("activo").activo.ticker, "T1")
        self.assertEqual(grafico.llamadas[0], ("obtener_datos", 1, I.H1))        # intervalo inicial: 1 h
        self.assertEqual(self._graficos(vista)[-1][1], ("DATOS_EN_VIVO", I.H1))

    def test_el_precio_en_vivo_se_aplica_segun_el_tipo_de_activo(self):
        vista, _, grafico, controlador = self._crear(_item(tipo=TipoActivo.ACCION))
        controlador.mostrar_activo(1)
        llamada = next(c for c in grafico.llamadas if c[0] == "con_precio")
        self.assertEqual(llamada[3:], (I.H1, TipoActivo.ACCION))

    def test_un_precio_igual_al_anterior_no_redibuja_el_grafico(self):
        vista, *_, controlador = self._crear()
        controlador.cargar()
        controlador.mostrar_activo(1)
        n = len(self._graficos(vista))
        vista.programadas[-1][1]()                                  # siguiente ciclo, mismo precio
        self.assertEqual(len(self._graficos(vista)), n)

    def test_volver_a_elegir_el_mismo_activo_no_hace_nada(self):
        vista, mercado, *_ , controlador = self._crear()
        controlador.mostrar_activo(1)
        n = len(mercado.llamadas)
        controlador.mostrar_activo(1)
        self.assertEqual(len(mercado.llamadas), n)

    def test_cambiar_de_intervalo_recarga_las_velas_y_no_mezcla_intervalos(self):
        vista, _, grafico, controlador = self._crear()
        controlador.mostrar_activo(1)
        vista.acciones["al_cambiar_intervalo"](I.D1)
        pedidos = [c for c in grafico.llamadas if c[0] == "obtener_datos"]
        self.assertEqual(pedidos[-1], ("obtener_datos", 1, I.D1))
        self.assertEqual(self._graficos(vista)[-1][1][1], I.D1)
        vista.acciones["al_cambiar_intervalo"](I.D1)                # mismo intervalo: no hace nada
        self.assertEqual(len([c for c in grafico.llamadas if c[0] == "obtener_datos"]), 2)

    def test_cambiar_de_intervalo_sin_activo_elegido_no_pide_velas(self):
        vista, _, grafico, _ = self._crear()
        vista.acciones["al_cambiar_intervalo"](I.D1)
        self.assertEqual(grafico.llamadas, [])

    def test_la_respuesta_de_un_intervalo_viejo_se_descarta(self):
        vista, _, _, controlador = self._crear()
        controlador.mostrar_activo(1)
        ejecutor = EjecutorDiferido()
        with mock.patch(_HILO, ejecutor):
            controlador.cambiar_intervalo(I.M15)     # petición A
            controlador.cambiar_intervalo(I.W1)      # petición B
            ejecutor.terminar_todo()
        self.assertEqual([g[1][1] for g in self._graficos(vista)][-1], I.W1)
        self.assertNotIn(I.M15, [g[1][1] for g in self._graficos(vista)][1:])

    def test_la_respuesta_de_un_activo_que_ya_no_esta_elegido_se_descarta(self):
        vista = VistaPanelFalsa()
        class MercadoQueDevuelveElPedido:
            def obtener_activo(self, id_activo): return _item(id_activo)
        controlador = GraficoController(vista, MercadoQueDevuelveElPedido(),
                                        ServicioGenerico(obtener_datos="DATOS", con_precio="EN_VIVO"))
        ejecutor = EjecutorDiferido()
        with mock.patch(_HILO, ejecutor):
            controlador.mostrar_activo(1)            # respuestas pendientes del activo 1
            controlador.mostrar_activo(2)            # el usuario eligió otro
            ejecutor.terminar_todo()
        self.assertEqual([e[1].activo.id_activo for e in vista.eventos if e[0] == "activo"], [2])

    def test_un_activo_inexistente_muestra_el_error(self):
        vista, *_, controlador = self._crear(ErrorOperacionInvalida("No existe"))
        controlador.mostrar_activo(1)
        self.assertEqual(vista.error, "No existe")

    def test_cada_30_segundos_recarga_las_velas(self):
        vista, _, grafico, controlador = self._crear()
        controlador.cargar()
        controlador.mostrar_activo(1)
        for _ in range(15):
            vista.programadas[-1][1]()
        self.assertEqual(len([c for c in grafico.llamadas if c[0] == "obtener_datos"]), 2)

    def test_si_la_pantalla_ya_no_existe_no_programa_mas(self):
        vista, *_, controlador = self._crear()
        vista.viva = False
        controlador.cargar()
        self.assertEqual(vista.programadas, [])


if __name__ == "__main__":
    unittest.main()
