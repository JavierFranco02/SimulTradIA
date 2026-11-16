"""Pruebas del eje horizontal del gráfico: qué marcas lleva y qué dice cada una."""
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

from simultradia.domain.entities.vela_entity import Vela
from simultradia.domain.enums import IntervaloVela as I
from simultradia.iu.components.candle_render import etiquetas_eje_x, indices_eje_x, texto_de_vela


def _velas(inicio, paso, n):
    return [Vela(inicio + paso * i, D(1), D(2), D(1), D(2), D(1)) for i in range(n)]


class PruebasEjeX(unittest.TestCase):
    def test_las_marcas_se_reparten_parejo_y_incluyen_la_primera_vela(self):
        marcas = indices_eje_x(120)
        self.assertEqual(marcas[0], 0)
        self.assertTrue(6 <= len(marcas) <= 10)
        self.assertEqual(indices_eje_x(0), [])
        self.assertEqual(indices_eje_x(3), [0, 1, 2])

    def test_en_velas_de_horas_cada_marca_lleva_la_hora_y_la_fecha_solo_al_cambiar_de_dia(self):
        velas = _velas(datetime(2026, 10, 19, 0, 0, tzinfo=timezone.utc), timedelta(hours=1), 72)
        marcas = list(range(0, 72, 6))
        etiquetas = etiquetas_eje_x(velas, marcas, I.H1)
        dias = [velas[i].momento.astimezone().date() for i in marcas]
        for etiqueta, dia, anterior in zip(etiquetas, dias, [None] + dias[:-1]):
            primera = etiqueta.split("\n")[0]
            self.assertRegex(primera, r"^\d\d:\d\d$")                 # siempre la hora
            self.assertEqual("\n" in etiqueta, anterior is None or dia != anterior)

    def test_en_velas_diarias_va_la_fecha_y_el_ano_solo_al_cambiar(self):
        velas = _velas(datetime(2026, 12, 20, tzinfo=timezone.utc), timedelta(days=1), 25)
        etiquetas = etiquetas_eje_x(velas, [0, 5, 10, 15], I.D1)
        self.assertEqual(etiquetas[0].split("\n")[1], "2026")           # la primera lleva el año
        self.assertNotIn("\n", etiquetas[1])
        self.assertEqual(etiquetas[3].split("\n")[1], "2027")           # cambió el año
        self.assertRegex(etiquetas[1], r"^\d{1,2} [a-z]{3}$")

    def test_el_texto_de_la_vela_lleva_la_fecha_y_la_hora_solo_si_aplica(self):
        vela = _velas(datetime(2026, 10, 19, 16, 30, tzinfo=timezone.utc), timedelta(hours=1), 1)[0]
        self.assertRegex(texto_de_vela(vela, True), r"^\d\d/\d\d/2026 \d\d:\d\d   O ")
        self.assertRegex(texto_de_vela(vela, False), r"^\d\d/\d\d/2026   O ")


if __name__ == "__main__":
    unittest.main()
