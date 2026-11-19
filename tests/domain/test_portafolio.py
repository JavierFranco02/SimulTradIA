"""Pruebas de las reglas puras de Portafolio."""
import unittest
from datetime import datetime, timezone
from decimal import Decimal as D

from simultradia.domain.entities.operacion_cerrada_entity import OperacionCerrada
from simultradia.domain.reglas.portafolio import (
    estadisticas_operaciones, exposicion_pct, ganancia_pct, rentabilidad_pct)

AHORA = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)


def _op(ganancia, comisiones="1", entrada="100", cantidad="2"):
    return OperacionCerrada(1, 1, D(cantidad), D(entrada), D(entrada), D(comisiones), D(ganancia), AHORA, AHORA)


class PruebasPorcentajes(unittest.TestCase):
    def test_rentabilidad_contra_el_capital_inicial(self):
        self.assertEqual(rentabilidad_pct(D("10842.15"), D("10000")), D("8.4215"))
        self.assertEqual(rentabilidad_pct(D("9000"), D("10000")), D("-10"))
        self.assertEqual(rentabilidad_pct(D("5"), D("0")), D("0"))

    def test_exposicion_es_la_parte_invertida(self):
        self.assertEqual(exposicion_pct(D("2500"), D("10000")), D("25"))
        self.assertEqual(exposicion_pct(D("0"), D("10000")), D("0"))
        self.assertEqual(exposicion_pct(D("10"), D("0")), D("0"))

    def test_ganancia_sobre_lo_que_costo_lo_vendido(self):
        self.assertEqual(ganancia_pct(_op("10")), D("5"))        # 10 sobre 100 x 2 = 200
        self.assertEqual(ganancia_pct(_op("-20")), D("-10"))
        self.assertEqual(ganancia_pct(_op("5", entrada="0")), D("0"))


class PruebasEstadisticas(unittest.TestCase):
    def test_mezcla_de_ganadoras_y_perdedoras(self):
        e = estadisticas_operaciones([_op("100"), _op("50"), _op("-30"), _op("-20", comisiones="2")])
        self.assertEqual((e.total, e.ganadoras, e.tasa_aciertos), (4, 2, D("50")))
        self.assertEqual(e.factor_beneficio, D("3"))              # 150 / 50
        self.assertEqual((e.ganancia_media, e.perdida_media, e.por_operacion), (D("75"), D("-25"), D("25")))
        self.assertEqual((e.mejor, e.peor, e.ganancia_total, e.comisiones), (D("100"), D("-30"), D("100"), D("5")))

    def test_sin_operaciones_todo_es_none_y_los_totales_cero(self):
        e = estadisticas_operaciones([])
        self.assertEqual((e.total, e.ganadoras, e.ganancia_total, e.comisiones), (0, 0, D("0"), D("0")))
        for valor in (e.tasa_aciertos, e.factor_beneficio, e.ganancia_media, e.perdida_media,
                      e.por_operacion, e.mejor, e.peor):
            self.assertIsNone(valor)

    def test_sin_perdidas_no_hay_factor_de_beneficio_ni_perdida_media(self):
        e = estadisticas_operaciones([_op("10"), _op("20")])
        self.assertEqual(e.tasa_aciertos, D("100"))
        self.assertIsNone(e.factor_beneficio)
        self.assertIsNone(e.perdida_media)

    def test_sin_ganancias_el_factor_es_cero(self):
        e = estadisticas_operaciones([_op("-10")])
        self.assertEqual((e.factor_beneficio, e.tasa_aciertos, e.ganancia_media), (D("0"), D("0"), None))

    def test_una_operacion_en_cero_no_es_ganadora_ni_perdedora(self):
        e = estadisticas_operaciones([_op("0"), _op("10")])
        self.assertEqual((e.total, e.ganadoras, e.tasa_aciertos), (2, 1, D("50")))
        self.assertIsNone(e.perdida_media)


if __name__ == "__main__":
    unittest.main()
