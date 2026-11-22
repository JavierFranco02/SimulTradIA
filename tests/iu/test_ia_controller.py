"""Pruebas del controlador de Predicciones IA (volatilidad), con vista y servicio FALSOS."""
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest import mock

from simultradia.core.exceptions import ErrorOperacionInvalida
from simultradia.domain.entities.prediccion_volatilidad_entity import (
    PrecisionVivo, PrediccionVolatilidad, SenalVolatilidad)
from simultradia.domain.enums import NivelVolatilidad
from simultradia.iu.ia.ia_controller import IAController
from simultradia.services.prediccion_volatilidad_service import DetalleActivoVolatilidad, ResumenVolatilidad
from tests.fakes import EjecutorDiferido, en_el_acto

_HILO = "simultradia.iu.base.panel_controller.ejecutar_en_hilo"
_AHORA = datetime(2026, 11, 18, tzinfo=timezone.utc)


def _senal(id_activo, rango, id_prediccion=None):
    p = PrediccionVolatilidad(id_activo, 1, _AHORA, _AHORA, Decimal(100), rango, rango * 0.7, rango * 1.4, 0.02, 0.02,
                              0.01, 0.03, NivelVolatilidad.NORMAL, id_prediccion=id_prediccion or id_activo * 10)
    return SenalVolatilidad(p, "T%d" % id_activo, "Activo %d" % id_activo)


class ServicioFalso:
    def __init__(self, senales=(), con_modelo=True):
        self.senales, self.con_modelo = list(senales), con_modelo
        self.llamadas = []
        self.error_proyeccion = None

    def resumen(self):
        self.llamadas.append(("resumen",))
        return ResumenVolatilidad(object() if self.con_modelo else None, list(self.senales),
                                  PrecisionVivo(0, 0, None, None, 0))

    def detalle(self, id_activo):
        self.llamadas.append(("detalle", id_activo))
        vigente = next((s.prediccion for s in self.senales if s.prediccion.id_activo == id_activo), None)
        return DetalleActivoVolatilidad(vigente, [])

    def proyectar(self, id_activo, dias, nivel=None):
        self.llamadas.append(("proyectar", id_activo, dias, nivel))
        if self.error_proyeccion:
            raise self.error_proyeccion
        return "PROYECCION"


class VistaIAFalsa:
    def __init__(self, nivel=""):
        self.viva, self.nivel = True, nivel
        self.acciones, self.programadas, self.eventos, self.errores = {}, [], [], []

    def esta_viva(self): return self.viva
    def vincular_acciones(self, **acciones): self.acciones = acciones
    def programar(self, ms, accion): self.programadas.append((ms, accion))
    def texto_nivel(self): return self.nivel
    def mostrar_error(self, texto): self.errores.append(texto)
    def datos_de(self, id_activo): return ("T%d" % id_activo, "Activo %d" % id_activo)
    def mostrar_resumen(self, resumen): self.eventos.append(("resumen",))
    def seleccionar(self, id_activo): self.eventos.append(("seleccionar", id_activo))
    def limpiar_detalle(self): self.eventos.append(("limpiar",))
    def mostrar_detalle(self, ticker, nombre, detalle): self.eventos.append(("detalle", ticker))
    def mostrar_proyeccion(self, proyeccion, nivel): self.eventos.append(("proyeccion", proyeccion, nivel))
    def proyeccion_no_disponible(self, texto): self.eventos.append(("sin_proyeccion", texto))

    def de_tipo(self, nombre):
        return [e for e in self.eventos if e[0] == nombre]


class PruebasIAController(unittest.TestCase):
    def setUp(self):
        parche = mock.patch(_HILO, en_el_acto)
        parche.start()
        self.addCleanup(parche.stop)

    def _crear(self, senales=(_senal(2, 0.03), _senal(1, 0.02)), **vista_args):
        vista, servicio = VistaIAFalsa(**vista_args), ServicioFalso(senales)
        return vista, servicio, IAController(vista, servicio)

    def test_al_cargar_pide_el_resumen_elige_el_primero_y_pide_su_detalle(self):
        vista, servicio, controlador = self._crear()
        controlador.cargar()
        self.assertEqual(servicio.llamadas, [("resumen",), ("detalle", 2), ("proyectar", 2, 5, None)])
        self.assertEqual(vista.de_tipo("seleccionar"), [("seleccionar", 2)])
        self.assertEqual(vista.de_tipo("detalle"), [("detalle", "T2")])
        self.assertEqual([ms for ms, _ in vista.programadas], [60000])

    def test_el_refresco_no_vuelve_a_pedir_el_detalle_si_nada_cambio(self):
        vista, servicio, controlador = self._crear()
        controlador.cargar()
        vista.programadas[-1][1]()
        self.assertEqual([l[0] for l in servicio.llamadas], ["resumen", "detalle", "proyectar", "resumen"])

    def test_si_la_prediccion_vigente_cambia_el_detalle_se_pide_de_nuevo(self):
        vista, servicio, controlador = self._crear()
        controlador.cargar()
        servicio.senales = [_senal(2, 0.03, id_prediccion=999), _senal(1, 0.02)]
        vista.programadas[-1][1]()
        self.assertEqual([l[0] for l in servicio.llamadas].count("detalle"), 2)

    def test_sin_modelo_no_elige_nada(self):
        vista = VistaIAFalsa()
        IAController(vista, ServicioFalso(con_modelo=False)).cargar()
        self.assertEqual(vista.de_tipo("seleccionar"), [])

    def test_calcular_nivel_acepta_coma_decimal_y_vacio_lo_quita(self):
        vista, servicio, controlador = self._crear(nivel="150,5")
        controlador.cargar()
        vista.acciones["al_calcular_nivel"]()
        self.assertEqual(servicio.llamadas[-1], ("proyectar", 2, 5, 150.5))
        vista.nivel = ""
        vista.acciones["al_calcular_nivel"]()
        self.assertEqual(servicio.llamadas[-1], ("proyectar", 2, 5, None))

    def test_un_nivel_invalido_avisa_y_no_pide_nada(self):
        vista, servicio, controlador = self._crear(nivel="abc")
        controlador.cargar()
        antes = len(servicio.llamadas)
        vista.acciones["al_calcular_nivel"]()
        vista.nivel = "-3"
        vista.acciones["al_calcular_nivel"]()
        self.assertEqual(len(vista.errores), 2)
        self.assertEqual(len(servicio.llamadas), antes)

    def test_si_faltan_velas_la_proyeccion_se_explica_sin_dialogo_de_error(self):
        vista, servicio, controlador = self._crear()
        servicio.error_proyeccion = ErrorOperacionInvalida("Faltan velas")
        controlador.cargar()
        self.assertEqual(vista.de_tipo("sin_proyeccion"), [("sin_proyeccion", "Faltan velas")])
        self.assertEqual(vista.errores, [])

    def test_una_respuesta_vieja_se_descarta(self):
        vista, servicio, controlador = self._crear()
        ejecutor = EjecutorDiferido()
        with mock.patch(_HILO, ejecutor):
            controlador.cargar()
            vista.acciones["al_elegir_activo"](2)
            controlador.cargar()
            ejecutor.terminar_todo()
        self.assertEqual(len(vista.de_tipo("resumen")), 1)

    def test_si_la_pantalla_ya_no_existe_no_la_toca(self):
        vista, _, controlador = self._crear()
        vista.viva = False
        controlador.cargar()
        self.assertEqual((vista.eventos, vista.programadas), ([], []))


if __name__ == "__main__":
    unittest.main()
