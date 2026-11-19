"""Pruebas de la generación y evaluación de predicciones (repositorios en memoria, scikit-learn)."""
import unittest
from datetime import timedelta

from simultradia.analisis.features import etiquetar
from simultradia.core.exceptions import ErrorOperacionInvalida
from simultradia.domain.entities.activo_entity import Activo
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.domain.enums import IntervaloVela, RolUsuario, TipoActivo
from simultradia.domain.reglas.prediccion import DIRECCIONES
from simultradia.services.modelo_ia_service import ModeloIAService
from simultradia.services.prediccion_service import PrediccionService
from tests.fakes import DatabaseFalsa, RepoActivoFalso, RepoPrecioFalso
from tests.services.ia_fakes import (
    AHORA, AlmacenFalso, ModeloRepoFalso, PrediccionRepoFalso, crear_modelo_prueba, serie_ciclica, velas_desde)

ADMIN = Usuario("Jefe", "j@x.com", "h", rol=RolUsuario.ADMIN, id_usuario=1)
AYER = AHORA.replace(hour=0, minute=0) - timedelta(days=1)
FUTURO = 40          # velas posteriores a AHORA, para poder evaluar más adelante


class PruebasPrediccionService(unittest.TestCase):
    def setUp(self):
        self.reloj = [AHORA]
        self.precios = RepoPrecioFalso()
        self.activos = [Activo("A1", "Activo 1", TipoActivo.CRIPTO, id_activo=1),
                        Activo("A2", "Activo 2", TipoActivo.ACCION, id_activo=2),
                        Activo("A3", "Activo 3", TipoActivo.CRIPTO, id_activo=3)]
        self.cierres = {}
        for a in self.activos:
            self.cierres[a.id_activo] = serie_ciclica(900 + FUTURO, a.id_activo)
            self.precios.velas[(a.id_activo, IntervaloVela.D1)] = velas_desde(
                self.cierres[a.id_activo], AYER + timedelta(days=FUTURO))
        repo_activos = RepoActivoFalso(self.activos, self.precios)
        self.modelos, self.almacen, self.predicciones = ModeloRepoFalso(), AlmacenFalso(), PrediccionRepoFalso()
        ahora = lambda: self.reloj[0]
        entrenador = ModeloIAService(DatabaseFalsa(), repo_activos, self.precios, self.modelos, self.almacen,
                                     crear_modelo=crear_modelo_prueba, ahora=ahora)
        self.entrenador = entrenador
        self.servicio = PrediccionService(DatabaseFalsa(), repo_activos, self.precios, self.modelos,
                                          self.predicciones, self.almacen, ahora=ahora)

    def _entrenar(self, horizonte=5):
        self.assertTrue(self.entrenador.entrenar(ADMIN, horizonte).activado)

    def test_sin_modelo_activo_no_genera_nada(self):
        self.assertEqual(self.servicio.generar_predicciones().generadas, 0)
        self.assertEqual(self.predicciones.predicciones, [])

    def test_genera_una_por_activo_y_no_repite_en_el_mismo_dia(self):
        self._entrenar()
        self.assertEqual(self.servicio.generar_predicciones().generadas, 3)
        self.assertEqual(self.servicio.generar_predicciones().generadas, 0)
        for p in self.predicciones.predicciones:
            self.assertAlmostEqual(p.prob_alcista + p.prob_bajista + p.prob_lateral, 1.0, delta=0.001)
            self.assertAlmostEqual(p.confianza, max(p.prob_alcista, p.prob_bajista, p.prob_lateral))
            self.assertGreater(p.fecha_objetivo, p.generada_en)
            self.assertEqual(p.horizonte_dias, 5)
        manana = AHORA + timedelta(days=1)
        self.reloj[0] = manana
        self.assertEqual(self.servicio.generar_predicciones().generadas, 3)

    def test_la_referencia_es_el_cierre_de_la_ultima_vela_cerrada(self):
        self._entrenar()
        self.servicio.generar_predicciones()
        p = self.predicciones.predicciones[0]
        velas = self.precios.velas[(p.id_activo, IntervaloVela.D1)]
        ayer = next(v for v in velas if v.momento == AYER)
        self.assertEqual(p.precio_referencia, ayer.cierre)

    def test_omite_el_activo_cuya_ultima_vela_es_vieja(self):
        self._entrenar()
        vieja = velas_desde(self.cierres[1][:-FUTURO], AYER - timedelta(days=30))
        self.precios.velas[(1, IntervaloVela.D1)] = vieja
        resultado = self.servicio.generar_predicciones()
        self.assertEqual((resultado.generadas, resultado.omitidas), (2, 1))
        self.assertNotIn(1, {p.id_activo for p in self.predicciones.predicciones})

    def test_evaluar_espera_a_que_venza_y_decide_el_acierto_con_la_misma_regla(self):
        self._entrenar()
        self.servicio.generar_predicciones()
        self.assertEqual(self.servicio.evaluar_vencidas(), 0)             # todavía no vence
        self.reloj[0] = AHORA + timedelta(days=12)
        self.assertEqual(self.servicio.evaluar_vencidas(), 3)
        self.assertEqual(self.servicio.evaluar_vencidas(), 0)             # ya no quedan pendientes
        for p in self.predicciones.predicciones:
            cierres = self.cierres[p.id_activo]
            i = len(cierres) - FUTURO - 1                                  # la vela de AYER
            clase = etiquetar(cierres, 5)[i]
            self.assertEqual(p.direccion_real, DIRECCIONES[clase])
            self.assertEqual(p.acierto, p.direccion == p.direccion_real)
            self.assertEqual(float(p.precio_resultado), cierres[i + 5])

    def test_resumen_trae_modelo_senales_ordenadas_y_precision(self):
        self.assertIsNone(self.servicio.resumen(5).modelo)
        self._entrenar()
        self.servicio.generar_predicciones()
        resumen = self.servicio.resumen(5)
        self.assertEqual(resumen.modelo.horizonte_dias, 5)
        self.assertEqual(len(resumen.senales), 3)
        confianzas = [s.prediccion.confianza for s in resumen.senales]
        self.assertEqual(confianzas, sorted(confianzas, reverse=True))
        self.assertEqual(resumen.precision.evaluadas, 0)
        self.assertEqual(self.servicio.resumen(3).senales, [])

    def test_detalle_trae_la_vigente_y_el_historial(self):
        self._entrenar()
        self.servicio.generar_predicciones()
        detalle = self.servicio.detalle(1, 5)
        self.assertEqual(detalle.vigente.id_activo, 1)
        self.assertEqual(len(detalle.historial), 1)
        self.assertIsNone(self.servicio.detalle(1, 3).vigente)

    def test_estado_del_ciclo_para_el_administrador(self):
        from simultradia.core.exceptions import ErrorPermisos
        self._entrenar()
        self.servicio.generar_predicciones()
        ciclo = self.servicio.estado_ciclo(ADMIN)
        self.assertEqual((ciclo.de_hoy, ciclo.pendientes, ciclo.evaluadas), (3, 3, 0))
        self.assertEqual(ciclo.ultima_generada_en, AHORA)
        self.reloj[0] = AHORA + timedelta(days=12)
        self.servicio.evaluar_vencidas()
        ciclo = self.servicio.estado_ciclo(ADMIN)
        self.assertEqual((ciclo.pendientes, ciclo.evaluadas), (0, 3))
        with self.assertRaises(ErrorPermisos):
            self.servicio.estado_ciclo(Usuario("Ana", "a@x.com", "h", id_usuario=2))

    def test_proyectar_usa_las_velas_cerradas_y_avisa_si_faltan(self):
        proyeccion = self.servicio.proyectar(1, 5, nivel=1.0)
        self.assertEqual(proyeccion.dias, 5)
        self.assertEqual(len(proyeccion.percentiles[50]), 5)
        self.assertIsNotNone(proyeccion.prob_tocar_nivel)
        self.precios.velas[(1, IntervaloVela.D1)] = self.precios.velas[(1, IntervaloVela.D1)][:10]
        with self.assertRaises(ErrorOperacionInvalida):
            self.servicio.proyectar(1, 5)


if __name__ == "__main__":
    unittest.main()
