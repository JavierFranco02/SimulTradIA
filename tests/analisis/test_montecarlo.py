"""Pruebas de la proyección Monte Carlo."""
import math
import random
import unittest

from simultradia.analisis.montecarlo import proyectar


def _serie(n=300, vol=0.01, semilla=3):
    azar = random.Random(semilla)
    precio, cierres = 100.0, []
    for _ in range(n):
        precio *= math.exp(azar.gauss(0, vol))
        cierres.append(precio)
    return cierres


class PruebasMonteCarlo(unittest.TestCase):
    def test_con_la_misma_semilla_da_lo_mismo(self):
        a = proyectar(_serie(), 5, 500, semilla=7)
        b = proyectar(_serie(), 5, 500, semilla=7)
        self.assertEqual(a.percentiles, b.percentiles)

    def test_los_percentiles_estan_ordenados_y_el_abanico_se_abre(self):
        p = proyectar(_serie(), 10, 2000, semilla=1).percentiles
        for d in range(10):
            self.assertTrue(p[5][d] <= p[25][d] <= p[50][d] <= p[75][d] <= p[95][d])
        self.assertGreater(p[95][9] - p[5][9], p[95][0] - p[5][0])

    def test_no_supone_tendencia(self):
        r = proyectar(_serie(), 5, 4000, semilla=2)
        self.assertAlmostEqual(r.prob_subir, 0.5, delta=0.05)

    def test_probabilidad_de_tocar_un_nivel(self):
        cierres = _serie()
        lejos = proyectar(cierres, 5, 1000, nivel=cierres[-1] * 0.5, semilla=1)
        cerca = proyectar(cierres, 5, 1000, nivel=cierres[-1] * 0.99, semilla=1)
        self.assertEqual(lejos.prob_tocar_nivel, 0.0)
        self.assertGreater(cerca.prob_tocar_nivel, 0.2)
        self.assertIsNone(proyectar(cierres, 5, 100, semilla=1).prob_tocar_nivel)

    def test_pocos_datos_da_error(self):
        with self.assertRaises(ValueError):
            proyectar([1.0] * 10, 5)


if __name__ == "__main__":
    unittest.main()
