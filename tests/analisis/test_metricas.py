"""Pruebas de las métricas de la curva de capital: caída, retornos diarios, volatilidad y Sharpe."""
import unittest
from datetime import datetime, timedelta, timezone

from simultradia.analisis.metricas import (
    DIAS_MINIMOS, caida_maxima, caidas, retornos_diarios, sharpe, volatilidad_anual)


def _dias(n, hora=12):
    inicio = datetime(2026, 10, 1, hora, tzinfo=timezone.utc)
    return [inicio + timedelta(days=i) for i in range(n)]


class PruebasCaidas(unittest.TestCase):
    def test_la_caida_se_mide_desde_el_maximo_alcanzado_hasta_ahi(self):
        resultado = caidas([100.0, 110.0, 99.0, 121.0, 108.9])
        for obtenido, esperado in zip(resultado, [0.0, 0.0, -10.0, 0.0, -10.0]):
            self.assertAlmostEqual(obtenido, esperado)

    def test_la_caida_maxima_es_la_peor(self):
        self.assertAlmostEqual(caida_maxima([100.0, 110.0, 99.0, 121.0, 118.0]), -10.0)

    def test_una_serie_que_solo_sube_no_tiene_caida(self):
        self.assertEqual(caida_maxima([1.0, 2.0, 3.0]), 0.0)

    def test_sin_datos(self):
        self.assertEqual((caidas([]), caida_maxima([])), ([], 0.0))


class PruebasRetornos(unittest.TestCase):
    def test_se_toma_el_ultimo_valor_de_cada_dia(self):
        base = datetime(2026, 10, 1, tzinfo=timezone.utc)
        momentos = [base + timedelta(hours=h) for h in (1, 5, 23, 25, 47)]     # día 1: 3 puntos; día 2: 2 puntos
        retornos = retornos_diarios(momentos, [100.0, 101.0, 102.0, 105.0, 107.1])
        self.assertEqual(len(retornos), 1)
        self.assertAlmostEqual(retornos[0], 107.1 / 102.0 - 1)

    def test_un_solo_dia_no_da_retornos(self):
        self.assertEqual(retornos_diarios(_dias(1), [100.0]), [])

    def test_un_valor_cero_no_divide_por_cero(self):
        self.assertEqual(retornos_diarios(_dias(3), [0.0, 10.0, 20.0]), [1.0])


class PruebasRiesgo(unittest.TestCase):
    def test_con_poco_historial_no_hay_volatilidad_ni_sharpe(self):
        retornos = [0.01, -0.01] * ((DIAS_MINIMOS - 1) // 2)
        self.assertLess(len(retornos), DIAS_MINIMOS)
        self.assertEqual((volatilidad_anual(retornos), sharpe(retornos)), (None, None))

    def test_con_historial_suficiente_se_calculan(self):
        retornos = [0.02, -0.01] * DIAS_MINIMOS
        self.assertGreater(volatilidad_anual(retornos), 0)
        self.assertGreater(sharpe(retornos), 0)               # en promedio gana
        self.assertLess(sharpe([-r for r in retornos]), 0)    # en promedio pierde

    def test_si_el_capital_no_se_movio_no_hay_sharpe(self):
        retornos = [0.0] * DIAS_MINIMOS
        self.assertEqual(volatilidad_anual(retornos), 0.0)
        self.assertIsNone(sharpe(retornos))


if __name__ == "__main__":
    unittest.main()
