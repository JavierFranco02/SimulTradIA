"""Pruebas del controlador de Administración · Modelos de IA, con vista y servicios FALSOS."""
import unittest
from types import SimpleNamespace
from unittest import mock

from simultradia.core.exceptions import ErrorOperacionInvalida
from simultradia.domain.entities.modelo_ia_entity import ModeloIA
from simultradia.domain.entities.prediccion_entity import EstadoCiclo
from simultradia.iu.admin.modelos_ia_controller import ModelosIAController, texto_resultado
from simultradia.services.modelo_ia_service import ComparacionAlgoritmo, ResultadoModelo
from tests.fakes import en_el_acto

_HILO = "simultradia.iu.base.panel_controller.ejecutar_en_hilo"
_EV = SimpleNamespace(veredicto="Supera la base", z=2.4149)
_EV_MALA = SimpleNamespace(veredicto="No se distingue del azar", z=0.5)


class ModeloServicioFalso:
    def __init__(self):
        self.llamadas, self.error = [], None

    def _responder(self, resultado):
        if self.error:
            raise self.error
        return resultado

    def entrenar(self, actor, horizonte):
        self.llamadas.append(("entrenar", actor, horizonte))
        return self._responder(ResultadoModelo(ModeloIA("direccion_5d", "v2"), _EV, True))

    def comparar(self, actor, horizonte):
        self.llamadas.append(("comparar", actor, horizonte))
        return self._responder([ComparacionAlgoritmo("LightGBM", _EV)])

    def activar(self, actor, id_modelo):
        self.llamadas.append(("activar", actor, id_modelo))
        return self._responder(None)

    def listar(self, actor):
        self.llamadas.append(("listar", actor))
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
    def mostrar_comparacion(self, horizonte, filas): self.eventos.append(("comparacion", horizonte, filas))


class PruebasModelosIAController(unittest.TestCase):
    def setUp(self):
        parche = mock.patch(_HILO, en_el_acto)
        parche.start()
        self.addCleanup(parche.stop)
        self.admin = object()

    def _crear(self, **vista_args):
        vista, servicio = VistaModelosFalsa(**vista_args), ModeloServicioFalso()
        controlador = ModelosIAController(vista, servicio, PrediccionServicioFalso(),
                                          SimpleNamespace(usuario=self.admin))
        return vista, servicio, controlador

    def test_cargar_muestra_versiones_y_ciclo_y_programa_el_refresco(self):
        vista, _, controlador = self._crear()
        controlador.cargar()
        self.assertEqual(vista.eventos[0][0], "estado")
        self.assertEqual([ms for ms, _ in vista.programadas], [10000])

    def test_entrenar_confirma_ocupa_los_botones_avisa_y_refresca(self):
        vista, servicio, _ = self._crear()
        vista.acciones["al_entrenar"](5)
        self.assertEqual(len(vista.confirmaciones), 1)
        self.assertEqual(servicio.llamadas[0], ("entrenar", self.admin, 5))
        self.assertEqual(vista.eventos[0], ("ocupado", True, "entrenar"))
        self.assertIn(("ocupado", False, "entrenar"), vista.eventos)
        self.assertFalse(vista.ocupado)
        self.assertIn("Quedó activo", vista.exitos[0])
        self.assertEqual(vista.eventos[-1][0], "estado")

    def test_si_el_administrador_no_confirma_no_se_entrena(self):
        vista, servicio, _ = self._crear(confirma=False)
        vista.acciones["al_entrenar"](5)
        self.assertEqual(servicio.llamadas, [])
        self.assertFalse(vista.ocupado)

    def test_no_se_lanza_otra_accion_mientras_hay_una_en_curso(self):
        vista, servicio, _ = self._crear()
        vista._ocupado = True
        for accion, valor in (("al_entrenar", 5), ("al_comparar", 5), ("al_activar", 1)):
            vista.acciones[accion](valor)
        self.assertEqual(servicio.llamadas, [])

    def test_un_error_al_entrenar_se_muestra_y_libera_los_botones(self):
        vista, servicio, _ = self._crear()
        servicio.error = ErrorOperacionInvalida("No hay velas diarias suficientes para entrenar.")
        vista.acciones["al_entrenar"](5)
        self.assertEqual(vista.errores, ["No hay velas diarias suficientes para entrenar."])
        self.assertFalse(vista.ocupado)

    def test_comparar_muestra_la_tabla(self):
        vista, servicio, _ = self._crear()
        vista.acciones["al_comparar"](3)
        self.assertEqual(servicio.llamadas[0], ("comparar", self.admin, 3))
        self.assertEqual(vista.eventos[-1], ("comparacion", 3, [("LightGBM", _EV)]))
        self.assertFalse(vista.ocupado)

    def test_activar_pide_confirmacion_y_refresca(self):
        vista, servicio, _ = self._crear()
        vista.acciones["al_activar"](7)
        self.assertEqual(servicio.llamadas[0], ("activar", self.admin, 7))
        self.assertEqual(vista.eventos[-1][0], "estado")
        vista2, servicio2, _ = self._crear(confirma=False)
        vista2.acciones["al_activar"](7)
        self.assertEqual(servicio2.llamadas, [])

    def test_texto_del_resultado(self):
        activo = texto_resultado(ResultadoModelo(ModeloIA("direccion_5d", "v2"), _EV, True))
        self.assertEqual(activo, "direccion_5d v2: supera la base (z = 2,41). Quedó activo.")
        no = texto_resultado(ResultadoModelo(ModeloIA("direccion_1d", "v1"), _EV_MALA, False))
        self.assertIn("No se activó", no)

    def test_si_la_pantalla_ya_no_existe_no_la_toca(self):
        vista, _, controlador = self._crear()
        vista.viva = False
        controlador.cargar()
        self.assertEqual((vista.eventos, vista.programadas), ([], []))


if __name__ == "__main__":
    unittest.main()
