"""Pruebas de las features y del objetivo de volatilidad: sin mirar el futuro y con la razón bien armada."""
import math
import unittest
from datetime import timedelta
from decimal import Decimal

from simultradia.analisis.volatilidad import (
    ARRANQUE, INDICE_NORMAL, NOMBRES_FEATURES, calcular_features, etiquetar, rango_de, rangos)
from simultradia.domain.entities.vela_entity import Vela
from tests.ia.vol_fakes import AYER, velas_vol


class PruebasVolatilidadFeatures(unittest.TestCase):
    def test_rango_es_maximo_menos_minimo_sobre_cierre(self):
        v = Vela(AYER, Decimal(100), Decimal(103), Decimal(100), Decimal(101), Decimal(1))
        self.assertAlmostEqual(rango_de(v), 3 / 101)

    def test_un_dia_sin_rango_usa_un_piso_para_poder_tomar_logaritmo(self):
        v = Vela(AYER, Decimal(100), Decimal(100), Decimal(100), Decimal(100), Decimal(1))
        self.assertGreater(rango_de(v), 0)

    def test_una_fila_por_vela_y_none_antes_del_arranque(self):
        velas = velas_vol(300, 1)
        filas = calcular_features(velas)
        self.assertEqual(len(filas), 300)
        self.assertTrue(all(f is None for f in filas[:ARRANQUE]))
        self.assertTrue(all(f is not None and len(f) == len(NOMBRES_FEATURES) for f in filas[ARRANQUE:]))

    def test_las_features_no_miran_el_futuro(self):
        velas = velas_vol(300, 2)
        completas = calcular_features(velas)
        cortadas = calcular_features(velas[:250])
        for i in range(ARRANQUE, 250):
            self.assertEqual(completas[i], cortadas[i])

    def test_el_objetivo_es_la_razon_del_rango_siguiente_con_lo_normal(self):
        velas = velas_vol(200, 3)
        objetivos = etiquetar(velas)
        i = 150
        r = rangos(velas)
        normal = sum(r[i - 19:i + 1]) / 20
        self.assertAlmostEqual(objetivos[i], math.log(r[i + 1]) - math.log(normal))
        self.assertIsNone(objetivos[-1])                   # la última vela no tiene siguiente

    def test_la_feature_normal_coincide_con_el_logaritmo_del_objetivo(self):
        velas = velas_vol(200, 4)
        fila = calcular_features(velas)[150]
        r = rangos(velas)
        self.assertAlmostEqual(fila[INDICE_NORMAL], math.log(sum(r[131:151]) / 20), places=9)

    def test_el_dia_de_la_semana_es_un_ciclo(self):
        velas = velas_vol(200, 5)
        filas = calcular_features(velas)
        i, j = 150, 157                                    # misma posición una semana después
        self.assertAlmostEqual(filas[i][-2], filas[j][-2])
        self.assertAlmostEqual(filas[i][-1], filas[j][-1])


if __name__ == "__main__":
    unittest.main()
