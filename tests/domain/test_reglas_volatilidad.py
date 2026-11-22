"""Pruebas de las reglas de volatilidad: niveles, umbrales, intervalo y fecha objetivo."""
import unittest
from datetime import datetime, timezone

from simultradia.domain.enums import NivelVolatilidad as N, TipoActivo
from simultradia.domain.reglas.volatilidad import (
    fecha_objetivo, intervalo_80, nivel_de, percentil, umbrales_de, velas_de_purga)


class PruebasReglasVolatilidad(unittest.TestCase):
    def test_percentil_interpola(self):
        self.assertAlmostEqual(percentil([1, 2, 3, 4, 5], 50), 3)
        self.assertAlmostEqual(percentil([1, 2, 3, 4, 5], 25), 2)
        self.assertAlmostEqual(percentil([1, 2], 50), 1.5)
        self.assertEqual(percentil([7], 90), 7)

    def test_umbrales_necesitan_historia(self):
        self.assertIsNone(umbrales_de([0.01] * 19))
        bajo, alto = umbrales_de([i / 1000 for i in range(1, 91)])
        self.assertLess(bajo, alto)

    def test_nivel_por_umbrales(self):
        self.assertEqual(nivel_de(0.005, 0.01, 0.02), N.BAJA)
        self.assertEqual(nivel_de(0.01, 0.01, 0.02), N.BAJA)
        self.assertEqual(nivel_de(0.015, 0.01, 0.02), N.NORMAL)
        self.assertEqual(nivel_de(0.02, 0.01, 0.02), N.ALTA)

    def test_intervalo_es_simetrico_en_logaritmo_y_contiene_al_rango(self):
        bajo, alto = intervalo_80(0.02, 0.3)
        self.assertLess(bajo, 0.02)
        self.assertGreater(alto, 0.02)
        self.assertAlmostEqual(bajo * alto, 0.02 ** 2)
        self.assertEqual(intervalo_80(0.02, 0.0), (0.02, 0.02))

    def test_fecha_objetivo_cripto_es_el_cierre_del_dia_siguiente(self):
        viernes = datetime(2026, 11, 20, tzinfo=timezone.utc)
        self.assertEqual(fecha_objetivo(viernes, TipoActivo.CRIPTO), datetime(2026, 11, 22, tzinfo=timezone.utc))

    def test_fecha_objetivo_de_una_accion_salta_el_fin_de_semana(self):
        viernes = datetime(2026, 11, 20, tzinfo=timezone.utc)
        self.assertEqual(fecha_objetivo(viernes, TipoActivo.ACCION), datetime(2026, 11, 24, tzinfo=timezone.utc))

    def test_purga(self):
        self.assertEqual(velas_de_purga(1), 5)


if __name__ == "__main__":
    unittest.main()
