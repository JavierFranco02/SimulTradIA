"""Pruebas de las features y la etiqueta: lo importante es que no miren al futuro."""
import math
import random
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from simultradia.analisis.features import (
    NOMBRES_FEATURES, calcular_features, etiquetar, umbral_de, velas_cerradas, volatilidad)
from simultradia.domain.entities.vela_entity import Vela
from simultradia.domain.reglas.prediccion import ALCISTA, BAJISTA, LATERAL

INICIO = datetime(2020, 1, 1, tzinfo=timezone.utc)


def _velas(cierres, volumen=1000):
    return [Vela(INICIO + timedelta(days=i), Decimal(str(c)), Decimal(str(c * 1.01)),
                 Decimal(str(c * 0.99)), Decimal(str(c)), Decimal(volumen))
            for i, c in enumerate(cierres)]


def _serie(n, semilla=1):
    azar = random.Random(semilla)
    precio, cierres = 100.0, []
    for _ in range(n):
        precio *= math.exp(azar.gauss(0, 0.01))
        cierres.append(round(precio, 4))
    return cierres


class PruebasFeatures(unittest.TestCase):
    def test_las_primeras_filas_no_tienen_features_y_el_largo_coincide(self):
        velas = _velas(_serie(80))
        filas = calcular_features(velas)
        self.assertEqual(len(filas), 80)
        self.assertTrue(all(f is None for f in filas[:50]))
        self.assertEqual(len(filas[60]), len(NOMBRES_FEATURES))

    def test_las_features_no_cambian_si_cambia_el_futuro(self):
        cierres = _serie(120)
        originales = calcular_features(_velas(cierres))
        alterados = cierres[:90] + [c * 3 for c in cierres[90:]]
        nuevas = calcular_features(_velas(alterados))
        for i in range(50, 90):
            self.assertEqual(originales[i], nuevas[i])
        self.assertNotEqual(originales[100], nuevas[100])

    def test_volatilidad_de_una_serie_constante_es_cero(self):
        vol = volatilidad([10.0] * 30, 20)
        self.assertIsNone(vol[19])
        self.assertEqual(vol[20], 0.0)

    def test_etiqueta_calculada_a_mano(self):
        cierres = [100.0 + (i % 2) for i in range(25)]      # retornos de +1 % / -1 %
        vol = volatilidad(cierres, 20)[20]
        umbral = umbral_de(vol, 1)
        etiquetas = etiquetar(cierres, 1)
        retorno = cierres[21] / cierres[20] - 1
        esperada = ALCISTA if retorno > umbral else BAJISTA if retorno < -umbral else LATERAL
        self.assertEqual(etiquetas[20], esperada)
        self.assertTrue(all(e is None for e in etiquetas[:20]))   # sin volatilidad todavía
        self.assertIsNone(etiquetas[-1])                          # sin futuro

    def test_etiqueta_detecta_subida_y_caida_grandes(self):
        base = _serie(40)
        sube = base + [base[-1] * 1.5]
        baja = base + [base[-1] * 0.5]
        self.assertEqual(etiquetar(sube, 1)[39], ALCISTA)
        self.assertEqual(etiquetar(baja, 1)[39], BAJISTA)

    def test_velas_cerradas_quita_la_vela_del_dia_en_curso(self):
        velas = _velas([1, 2, 3])
        ahora = INICIO + timedelta(days=2, hours=5)       # la vela del día 2 sigue abierta
        self.assertEqual(len(velas_cerradas(velas, ahora)), 2)
        self.assertEqual(len(velas_cerradas(velas, INICIO + timedelta(days=3))), 3)


if __name__ == "__main__":
    unittest.main()
