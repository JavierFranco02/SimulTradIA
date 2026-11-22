"""Pruebas del controlador de Administración · Modelos de IA (volatilidad), con vista y servicios FALSOS."""
import unittest
from types import SimpleNamespace
from unittest import mock

from simultradia.core.exceptions import ErrorOperacionInvalida
from simultradia.domain.entities.modelo_ia_entity import ModeloIA
from simultradia.domain.entities.prediccion_volatilidad_entity import EstadoCiclo
from simultradia.iu.admin.modelos_ia_controller import ModelosIAController, texto_resultado
from simultradia.services.modelo_volatilidad_service import ComparacionAlgoritmo, ResultadoModelo
from tests.fakes import en_el_acto

_HILO = "simultradia.iu.base.panel_controller.ejecutar_en_hilo"
_EV = SimpleNamespace(veredicto="Supera a las bases", z=2.4149, error=0.3)
_EV_MALA = SimpleNamespace(veredicto="No supera a las bases", z=0.5, error=0.4)


class ModeloServicioFalso:
    def __init__(self):
        self.llamadas, self.error = [], None

    def _responder(self, resultado):
        if self.error:
            raise self.error
        return resultado

    def entrenar(self, actor):
        self.llamadas.append(("entrenar", actor))
        return self._responder(ResultadoModelo(ModeloIA("volatilidad_1d", "v2"), _EV, True))

    def comparar(self, actor):
        self.llamadas.append(("comparar", actor))
        return self._responder([ComparacionAlgoritmo("LightGBM", _EV)])

    def activar(self, actor, id_modelo):
        self.llamadas.append(("activar", actor, id_modelo))
        return self._responder(None)

    def listar(self, actor):
        return ["MODELOS"]


class PrediccionServicioFalso:
    def estado_ciclo(self, actor):
        return EstadoCiclo(None, 0, 0, 0)


class VistaModelosFalsa:
    def __init__(self, confirma=True):
        self.viva, self._ocupado, self.confirma = True, False, confirma
        self.acciones, self.programadas, self.eventos = {}, [], []
        self.errores, self.exitos, self.confirmaciones = [], [], []

    @property
    def ocupado(self): return self._ocupado
    def esta_viva(self): return self.viva
    def vincular_acciones(self, **acciones): self.acciones = acciones
    def programar(self, ms, accion): self.programadas.append((ms, accion))
    def confirmar(self, mensaje):
        self.confirmaciones.append(mensaje)
        return self.confirma
    def establecer_ocupado(self, ocupado, accion="entrenar"):
        self._ocupado = ocupado
        self.eventos.append(("ocupado", ocupado, accion))
    def mostrar_error(self, texto): self.errores.append(texto)
    def mostrar_exito(self, texto): self.exitos.append(texto)
    def mostrar_estado(self, modelos, ciclo): self.eventos.append(("estado", modelos))
    def mostrar_comparacion(self, filas): self.eventos.append(("comparacion", filas))


class PruebasModelosController(unittest.TestCase):
    def setUp(self):
        parche = mock.patch(_HILO, en_el_acto)
        parche.start()
        self.addCleanup(parche.stop)
        self.admin = object()

    def _crear(self, **vista_args):
        vista, servicio = VistaModelosFalsa(**vista_args), ModeloServicioFalso()
        ModelosIAController(vista, servicio, PrediccionServicioFalso(), SimpleNamespace(usuario=self.admin))
        return vista, servicio

    def test_entrenar_confirma_ocupa_los_botones_avisa_y_refresca(self):
        vista, servicio = self._crear()
        vista.acciones["al_entrenar"]()
        self.assertEqual(len(vista.confirmaciones), 1)
        self.assertEqual(servicio.llamadas[0], ("entrenar", self.admin))
        self.assertEqual(vista.eventos[0], ("ocupado", True, "entrenar"))
        self.assertFalse(vista.ocupado)
        self.assertIn("Quedó activo", vista.exitos[0])
        self.assertEqual(vista.eventos[-1][0], "estado")

    def test_sin_confirmar_no_se_entrena(self):
        vista, servicio = self._crear(confirma=False)
        vista.acciones["al_entrenar"]()
        self.assertEqual(servicio.llamadas, [])

    def test_no_se_lanza_otra_accion_mientras_hay_una_en_curso(self):
        vista, servicio = self._crear()
        vista._ocupado = True
        vista.acciones["al_entrenar"]()
        vista.acciones["al_comparar"]()
        vista.acciones["al_activar"](1)
        self.assertEqual(servicio.llamadas, [])

    def test_un_error_se_muestra_y_libera_los_botones(self):
        vista, servicio = self._crear()
        servicio.error = ErrorOperacionInvalida("No hay velas diarias suficientes.")
        vista.acciones["al_entrenar"]()
        self.assertEqual(vista.errores, ["No hay velas diarias suficientes."])
        self.assertFalse(vista.ocupado)

    def test_comparar_y_activar(self):
        vista, servicio = self._crear()
        vista.acciones["al_comparar"]()
        self.assertEqual(vista.eventos[-1], ("comparacion", [("LightGBM", _EV)]))
        vista.acciones["al_activar"](7)
        self.assertEqual(servicio.llamadas[-1], ("activar", self.admin, 7))

    def test_texto_del_resultado(self):
        self.assertEqual(texto_resultado(ResultadoModelo(ModeloIA("volatilidad_1d", "v2"), _EV, True)),
                         "volatilidad_1d v2: supera a las bases (z = 2,41; error ±35 %). Quedó activo.")
        self.assertIn("No se activó", texto_resultado(ResultadoModelo(ModeloIA("volatilidad_1d", "v1"), _EV_MALA, False)))


if __name__ == "__main__":
    unittest.main()
