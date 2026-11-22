"""Pruebas del entrenamiento, la generación y la evaluación de volatilidad (repositorios en memoria, scikit-learn)."""
import unittest
from datetime import timedelta

from simultradia.core.exceptions import ErrorOperacionInvalida, ErrorPermisos
from simultradia.domain.entities.activo_entity import Activo
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.domain.enums import EstadoModelo, IntervaloVela, NivelVolatilidad, RolUsuario, TipoActivo, TipoModeloIA
from simultradia.ia.volatilidad_serializacion import desde_dict
from simultradia.services.modelo_volatilidad_service import ModeloVolatilidadService
from simultradia.services.prediccion_volatilidad_service import PrediccionVolatilidadService
from tests.fakes import DatabaseFalsa, RepoActivoFalso, RepoPrecioFalso
from tests.ia.vol_fakes import (
    AHORA, AYER, AlmacenFalso, ModeloRepoFalso, PrediccionRepoFalso, crear_modelo_prueba, velas_azar, velas_vol)

ADMIN = Usuario("Jefe", "j@x.com", "h", rol=RolUsuario.ADMIN, id_usuario=1)
NORMAL = Usuario("Ana", "a@x.com", "h", id_usuario=2)
FUTURO = 6           # velas posteriores a AHORA, para evaluar más adelante


def armar(generador, activos=3, dias=700, futuro=0):
    precios = RepoPrecioFalso()
    lista = [Activo("A%d" % i, "Activo %d" % i, TipoActivo.CRIPTO if i % 2 else TipoActivo.ACCION, id_activo=i)
             for i in range(1, activos + 1)]
    for a in lista:
        precios.velas[(a.id_activo, IntervaloVela.D1)] = generador(dias + futuro, a.id_activo,
                                                                    AYER + timedelta(days=futuro))
    return precios, lista


class PruebasModeloVolatilidadService(unittest.TestCase):
    def _servicio(self, generador, modelos=None):
        precios, lista = armar(generador)
        modelos = modelos or ModeloRepoFalso()
        almacen = AlmacenFalso()
        return (ModeloVolatilidadService(DatabaseFalsa(), RepoActivoFalso(lista, precios), precios, modelos, almacen,
                                         crear_modelo=crear_modelo_prueba, ahora=lambda: AHORA,
                                         algoritmos={"A": crear_modelo_prueba}), modelos, almacen)

    def test_un_modelo_que_supera_las_bases_queda_activo_y_guardado(self):
        servicio, modelos, almacen = self._servicio(velas_vol)
        resultado = servicio.entrenar(ADMIN)
        self.assertTrue(resultado.activado)
        m = modelos.modelos[0]
        self.assertEqual((m.nombre, m.version, m.tipo, m.estado),
                         ("volatilidad_1d", "v1", TipoModeloIA.VOLATILIDAD, EstadoModelo.ACTIVO))
        self.assertIn(m.ruta_artefacto, almacen.archivos)
        self.assertEqual(modelos.entrenamientos[m.id_modelo]["estado"], "completado")
        self.assertTrue(desde_dict(m.metricas).supera_base)

    def test_un_segundo_entrenamiento_archiva_al_anterior(self):
        servicio, modelos, _ = self._servicio(velas_vol)
        servicio.entrenar(ADMIN)
        servicio.entrenar(ADMIN)
        self.assertEqual([m.estado for m in modelos.modelos], [EstadoModelo.ARCHIVADO, EstadoModelo.ACTIVO])

    def test_un_modelo_que_no_supera_las_bases_no_se_activa_y_conserva_al_anterior(self):
        servicio, modelos, _ = self._servicio(velas_vol)
        servicio.entrenar(ADMIN)
        peor, _, _ = self._servicio(velas_azar, modelos)
        resultado = peor.entrenar(ADMIN)
        self.assertFalse(resultado.activado)
        self.assertEqual([m.estado for m in modelos.modelos], [EstadoModelo.ACTIVO, EstadoModelo.ARCHIVADO])

    def test_solo_el_administrador_y_activar_valida(self):
        servicio, modelos, _ = self._servicio(velas_vol)
        with self.assertRaises(ErrorPermisos):
            servicio.entrenar(NORMAL)
        with self.assertRaises(ErrorPermisos):
            servicio.comparar(NORMAL)
        with self.assertRaises(ErrorOperacionInvalida):
            servicio.activar(ADMIN, 99)
        servicio.entrenar(ADMIN)
        servicio.entrenar(ADMIN)
        servicio.activar(ADMIN, 1)                       # revertir a la v1 archivada
        self.assertEqual([m.estado for m in modelos.modelos], [EstadoModelo.ACTIVO, EstadoModelo.ARCHIVADO])

    def test_no_se_activa_un_modelo_que_no_supera_las_bases(self):
        servicio, modelos, _ = self._servicio(velas_azar)
        servicio.entrenar(ADMIN)
        with self.assertRaises(ErrorOperacionInvalida):
            servicio.activar(ADMIN, 1)

    def test_comparar_no_guarda_nada(self):
        servicio, modelos, _ = self._servicio(velas_vol)
        filas = servicio.comparar(ADMIN)
        self.assertEqual([f.algoritmo for f in filas], ["A"])
        self.assertEqual(modelos.modelos, [])

    def test_listar_solo_trae_los_de_volatilidad(self):
        servicio, modelos, _ = self._servicio(velas_vol)
        servicio.entrenar(ADMIN)
        from simultradia.domain.entities.modelo_ia_entity import ModeloIA
        modelos.insertar(None, ModeloIA("direccion_1d", "v1"))
        self.assertEqual([m.nombre for m in servicio.listar(ADMIN)], ["volatilidad_1d"])

    def test_un_fallo_deja_el_modelo_fallido(self):
        servicio, modelos, _ = self._servicio(velas_vol)
        servicio._crear_modelo = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
        with self.assertRaises(ErrorOperacionInvalida):
            servicio.entrenar(ADMIN)
        self.assertEqual(modelos.modelos[0].estado, EstadoModelo.FALLIDO)


class PruebasPrediccionVolatilidadService(unittest.TestCase):
    def setUp(self):
        self.reloj = [AHORA]
        self.precios, self.lista = armar(velas_vol, futuro=FUTURO)
        repo_activos = RepoActivoFalso(self.lista, self.precios)
        self.modelos, self.almacen, self.predicciones = ModeloRepoFalso(), AlmacenFalso(), PrediccionRepoFalso()
        ahora = lambda: self.reloj[0]
        self.entrenador = ModeloVolatilidadService(DatabaseFalsa(), repo_activos, self.precios, self.modelos,
                                                   self.almacen, crear_modelo=crear_modelo_prueba, ahora=ahora)
        self.servicio = PrediccionVolatilidadService(DatabaseFalsa(), repo_activos, self.precios, self.modelos,
                                                     self.predicciones, self.almacen, ahora=ahora)

    def _entrenar(self):
        self.assertTrue(self.entrenador.entrenar(ADMIN).activado)

    def test_sin_modelo_activo_no_genera_nada(self):
        self.assertEqual(self.servicio.generar_predicciones().generadas, 0)
        self.assertEqual(self.predicciones.predicciones, [])

    def test_genera_una_por_activo_y_no_repite_en_el_mismo_dia(self):
        self._entrenar()
        self.assertEqual(self.servicio.generar_predicciones().generadas, 3)
        self.assertEqual(self.servicio.generar_predicciones().generadas, 0)
        for p in self.predicciones.predicciones:
            self.assertGreater(p.rango_predicho, 0)
            self.assertLess(p.rango_bajo, p.rango_predicho)
            self.assertLess(p.rango_predicho, p.rango_alto)
            self.assertLess(p.umbral_bajo, p.umbral_alto)
            self.assertGreater(p.fecha_objetivo, p.generada_en)
        self.reloj[0] = AHORA + timedelta(days=1)
        self.assertEqual(self.servicio.generar_predicciones().generadas, 3)

    def test_el_nivel_sale_de_los_umbrales_guardados(self):
        self._entrenar()
        self.servicio.generar_predicciones()
        for p in self.predicciones.predicciones:
            esperado = (NivelVolatilidad.BAJA if p.rango_predicho <= p.umbral_bajo
                        else NivelVolatilidad.ALTA if p.rango_predicho >= p.umbral_alto else NivelVolatilidad.NORMAL)
            self.assertEqual(p.nivel, esperado)

    def test_la_referencia_es_el_cierre_de_la_ultima_vela_cerrada(self):
        self._entrenar()
        self.servicio.generar_predicciones()
        p = self.predicciones.predicciones[0]
        velas = self.precios.velas[(p.id_activo, IntervaloVela.D1)]
        self.assertEqual(p.precio_referencia, next(v for v in velas if v.momento == AYER).cierre)

    def test_omite_el_activo_cuya_ultima_vela_es_vieja(self):
        self._entrenar()
        self.precios.velas[(1, IntervaloVela.D1)] = velas_vol(500, 1, AYER - timedelta(days=30))
        resultado = self.servicio.generar_predicciones()
        self.assertEqual((resultado.generadas, resultado.omitidas), (2, 1))

    def test_omite_un_modelo_entrenado_con_otras_features(self):
        self._entrenar()
        self.modelos.modelos[0].parametros["features"] = ["otra"]
        self.assertEqual(self.servicio.generar_predicciones().generadas, 0)

    def test_evaluar_espera_a_que_cierre_la_vela_y_decide_el_nivel_con_los_umbrales_guardados(self):
        self._entrenar()
        self.servicio.generar_predicciones()
        self.assertEqual(self.servicio.evaluar_vencidas(), 0)              # todavía no venció
        self.reloj[0] = AHORA + timedelta(days=2)                         # ya existe la vela de «hoy» (cerrada)
        self.assertEqual(self.servicio.evaluar_vencidas(), 3)
        self.assertEqual(self.servicio.evaluar_vencidas(), 0)              # no se evalúa dos veces
        from simultradia.analisis.volatilidad import rango_de
        from simultradia.domain.reglas.volatilidad import nivel_de
        for p in self.predicciones.predicciones:
            velas = self.precios.velas[(p.id_activo, IntervaloVela.D1)]
            siguiente = next(v for v in velas if v.momento == AYER + timedelta(days=1))
            self.assertAlmostEqual(p.rango_real, rango_de(siguiente))
            self.assertEqual(p.nivel_real, nivel_de(p.rango_real, p.umbral_bajo, p.umbral_alto))
            self.assertEqual(p.acierto_nivel, p.nivel_real == p.nivel)

    def test_lecturas_para_las_pantallas(self):
        self.assertIsNone(self.servicio.resumen().modelo)
        self._entrenar()
        self.servicio.generar_predicciones()
        resumen = self.servicio.resumen()
        self.assertEqual(len(resumen.senales), 3)
        veces = [s.prediccion.veces_lo_normal for s in resumen.senales]
        self.assertEqual(veces, sorted(veces, reverse=True))
        detalle = self.servicio.detalle(1)
        self.assertEqual(detalle.vigente.id_activo, 1)
        self.assertEqual(len(detalle.historial), 1)
        self.assertEqual(self.servicio.estado_ciclo(ADMIN).de_hoy, 3)
        with self.assertRaises(ErrorPermisos):
            self.servicio.estado_ciclo(NORMAL)


if __name__ == "__main__":
    unittest.main()
