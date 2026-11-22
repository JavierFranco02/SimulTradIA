"""Pruebas del motor de volatilidad (scikit-learn en lugar de LightGBM): dataset, validación walk-forward y bases."""
import json
import unittest

import numpy as np

from simultradia.analisis.volatilidad import INDICE_NORMAL, NOMBRES_FEATURES
from simultradia.core.exceptions import ErrorOperacionInvalida
from simultradia.ia.volatilidad import (
    armar_dataset, entrenar, estadistico_z, explicar, predecir, tramos_walk_forward)
from simultradia.ia.volatilidad_serializacion import a_dict, desde_dict
from tests.ia.vol_fakes import crear_modelo_prueba, velas_azar, velas_vol


def _con(generador, activos=3, n=900):
    return armar_dataset({i: generador(n, i) for i in range(1, activos + 1)})


class PruebasMotorVolatilidad(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.predecible = entrenar(_con(velas_vol), crear_modelo_prueba)
        cls.azar = entrenar(_con(velas_azar), crear_modelo_prueba)

    def test_dataset_ordenado_por_dia_con_columnas_alineadas(self):
        ds = _con(velas_vol)
        self.assertEqual(ds.X.shape[1], len(NOMBRES_FEATURES))
        self.assertTrue(np.all(np.diff(ds.dias) >= 0))
        self.assertTrue(np.allclose(ds.ln_normal, ds.X[:, INDICE_NORMAL]))
        self.assertTrue(np.all(ds.umbral_bajo < ds.umbral_alto))

    def test_sin_velas_suficientes_avisa(self):
        with self.assertRaises(ErrorOperacionInvalida):
            armar_dataset({1: velas_vol(50, 1)})

    def test_los_tramos_son_consecutivos_y_no_se_solapan(self):
        tramos = tramos_walk_forward(range(1000))
        self.assertEqual(len(tramos), 4)
        for (_a, fin), (inicio, _b) in zip(tramos, tramos[1:]):
            self.assertEqual(inicio, fin + 1)

    def test_con_volatilidad_anticipable_le_gana_a_las_dos_bases(self):
        ev = self.predecible.evaluacion
        self.assertLess(ev.error, ev.error_hoy)
        self.assertLess(ev.error, ev.error_media)
        self.assertTrue(ev.supera_base, "z=%s,%s" % (ev.z_hoy, ev.z_media))
        self.assertEqual(ev.z, min(ev.z_hoy, ev.z_media))
        self.assertEqual(len(ev.tramos), 4)
        self.assertEqual(len(ev.calibracion), 5)

    def test_con_rangos_al_azar_no_se_activa(self):
        self.assertFalse(self.azar.evaluacion.supera_base)

    def test_la_calibracion_sube_con_lo_que_espera_el_modelo(self):
        reales = [b.real for b in self.predecible.evaluacion.calibracion]
        self.assertGreater(reales[-1], reales[0])

    def test_predecir_devuelve_un_rango_positivo_razonable(self):
        ds = _con(velas_vol)
        r = predecir(self.predecible.modelo, list(ds.X[-1]))
        self.assertGreater(r, 0)
        self.assertLess(r, 0.5)

    def test_explicar_sin_booster_no_devuelve_factores(self):
        self.assertEqual(explicar(self.predecible.modelo, [0.0] * len(NOMBRES_FEATURES)), [])

    def test_explicar_ordena_por_aporte_y_descarta_el_sesgo(self):
        n = len(NOMBRES_FEATURES)
        aportes = [0.0] * n
        aportes[3], aportes[7] = -0.5, 0.2

        class Booster:
            def predict(self, X, pred_contrib=False):
                assert pred_contrib
                return np.array([aportes + [9.9]])          # el último valor es el sesgo

        class Modelo:
            booster_ = Booster()

        factores = explicar(Modelo(), [0.0] * n, maximo=2)
        self.assertEqual(factores, [(NOMBRES_FEATURES[3], -0.5), (NOMBRES_FEATURES[7], 0.2)])

    def test_importancias_del_modelo_final_suman_uno_si_existen(self):
        imp = self.predecible.evaluacion.importancias
        if imp:
            self.assertAlmostEqual(sum(imp.values()), 1.0, places=6)

    def test_serializacion_ida_y_vuelta_por_json(self):
        ev = self.predecible.evaluacion
        de_vuelta = desde_dict(json.loads(json.dumps(a_dict(ev))))
        self.assertEqual(a_dict(de_vuelta), a_dict(ev))
        self.assertEqual(de_vuelta.supera_base, ev.supera_base)

    def test_estadistico_z(self):
        self.assertEqual(estadistico_z([0.1] * 5), 0.0)                  # muy pocos días
        self.assertEqual(estadistico_z([0.1] * 30), 0.0)                 # sin variación no hay z
        azar = np.random.RandomState(0)
        self.assertGreater(estadistico_z(list(azar.normal(0.5, 1, 200))), 3)
        self.assertLess(abs(estadistico_z(list(azar.normal(0, 1, 200)))), 3)


if __name__ == "__main__":
    unittest.main()
