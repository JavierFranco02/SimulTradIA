"""Pruebas del entrenamiento. Usan HistGradientBoosting de scikit-learn en lugar de LightGBM
(el motor es el mismo contrato: fit, predict_proba, classes_), así corren sin instalar lightgbm."""
import math
import random
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from simultradia.analisis.features import NOMBRES_FEATURES
from simultradia.core.exceptions import ErrorOperacionInvalida
from simultradia.domain.entities.vela_entity import Vela
from simultradia.domain.reglas.prediccion import Z_MINIMO, dias_de_purga
from simultradia.ia.entrenamiento import (
    armar_dataset, entrenar, estadistico_z, evaluar, explicar, predecir, tramos_walk_forward)

INICIO = datetime(2012, 1, 2, tzinfo=timezone.utc)


def _modelo():
    return HistGradientBoostingClassifier(max_iter=60, learning_rate=0.1, random_state=0)


def _velas(cierres):
    return [Vela(INICIO + timedelta(days=i), Decimal(str(c)), Decimal(str(c * 1.01)),
                 Decimal(str(c * 0.99)), Decimal(str(c)), Decimal(1000))
            for i, c in enumerate(cierres)]


def _aleatorio(n, semilla):
    azar = random.Random(semilla)
    precio, cierres = 100.0, []
    for _ in range(n):
        precio *= math.exp(azar.gauss(0, 0.01))
        cierres.append(round(precio, 4))
    return cierres


def _ciclico(n, semilla):
    """Precio que oscila con periodo fijo más ruido: la dirección sí se puede aprender."""
    azar = random.Random(semilla)
    fase = azar.random() * 6.28
    return [round(100.0 * math.exp(0.25 * math.sin(2 * math.pi * i / 30 + fase)
                                   + azar.gauss(0, 0.004)), 4) for i in range(n)]


def _dataset(generador, activos=8, dias=1500, horizonte=5):
    return armar_dataset({a: _velas(generador(dias, a)) for a in range(1, activos + 1)}, horizonte)


class PruebasEntrenamiento(unittest.TestCase):
    def test_tramos_son_consecutivos_y_no_se_solapan(self):
        dias = list(range(1000))
        tramos = tramos_walk_forward(dias)
        self.assertEqual(len(tramos), 4)
        for (_, fin), (inicio, _) in zip(tramos, tramos[1:]):
            self.assertEqual(inicio, fin + 1)
        self.assertEqual(tramos[-1][1], 999)

    def test_el_entrenamiento_siempre_termina_antes_de_la_prueba_menos_la_purga(self):
        dataset = _dataset(_aleatorio, activos=2, dias=600)
        purga = dias_de_purga(dataset.horizonte)
        for inicio, _ in tramos_walk_forward(dataset.dias):
            entrena = dataset.dias < inicio - purga
            self.assertLess(dataset.dias[entrena].max(), inicio - purga)

    def test_datos_aleatorios_no_superan_la_base(self):
        evaluacion = evaluar(_dataset(_aleatorio), _modelo)
        self.assertLess(evaluacion.z, Z_MINIMO)
        self.assertFalse(evaluacion.supera_base)
        self.assertEqual(evaluacion.veredicto, "No se distingue del azar")

    def test_datos_con_patron_superan_la_base(self):
        evaluacion = evaluar(_dataset(_ciclico), _modelo)
        self.assertGreater(evaluacion.z, Z_MINIMO)
        self.assertGreater(evaluacion.ventaja, 5.0)
        self.assertTrue(evaluacion.supera_base)

    def test_la_evaluacion_trae_todas_las_metricas_coherentes(self):
        ev = evaluar(_dataset(_ciclico, activos=4, dias=900), _modelo)
        self.assertEqual(len(ev.tramos), 4)
        self.assertEqual(sum(sum(f) for f in ev.confusion), ev.n_prueba)
        self.assertEqual(sum(b.n for b in ev.calibracion), ev.n_prueba)
        self.assertEqual(len(ev.calibracion), 5)
        self.assertIsNotNone(ev.auc)
        mejores, total = ev.activos_mejores
        self.assertTrue(0 <= mejores <= total <= 4)

    def test_entrenar_deja_modelo_e_importancias_que_suman_uno(self):
        resultado = entrenar(_dataset(_ciclico, activos=3, dias=700), _modelo)
        modelo = resultado.modelo
        fila = list(np.zeros(len(NOMBRES_FEATURES)))
        alcista, lateral, bajista = predecir(modelo, fila)
        self.assertAlmostEqual(alcista + lateral + bajista, 1.0, places=6)
        if resultado.evaluacion.importancias:
            self.assertAlmostEqual(sum(resultado.evaluacion.importancias.values()), 1.0, places=6)

    def test_estadistico_z(self):
        self.assertAlmostEqual(estadistico_z(0.5, 0.4, 100), 0.1 / (0.24 / 100) ** 0.5)
        self.assertEqual(estadistico_z(0.5, 0.4, 0), 0.0)
        self.assertEqual(estadistico_z(0.5, 1.0, 100), 0.0)

    def test_sin_velas_da_error_claro(self):
        with self.assertRaises(ErrorOperacionInvalida):
            armar_dataset({1: _velas(_aleatorio(30, 1))}, 5)

    def test_explicar_toma_los_aportes_de_la_clase_pedida(self):
        n = len(NOMBRES_FEATURES)

        class Booster:
            def predict(self, X, pred_contrib=False):
                bloque = lambda base: [base * (i + 1) for i in range(n)] + [0.0]
                return np.array([bloque(1.0) + bloque(-1.0) + bloque(0.5)])

        class Modelo:
            classes_ = np.array([0, 1, 2])
            booster_ = Booster()

        mejores = explicar(Modelo(), [0.0] * n, clase=2, maximo=3)
        self.assertEqual(len(mejores), 3)
        self.assertEqual(mejores[0][0], NOMBRES_FEATURES[-1])
        self.assertAlmostEqual(mejores[0][1], 0.5 * n)
        self.assertEqual(explicar(object(), [0.0] * n, 2), [])


if __name__ == "__main__":
    unittest.main()
