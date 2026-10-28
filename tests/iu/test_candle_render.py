"""Prueba que el gráfico de velas se dibuja de verdad (matplotlib, sin ventana)."""
import io
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from matplotlib.figure import Figure

from simultradia.domain.entities.vela_entity import Vela
from simultradia.domain.enums import IntervaloVela
from simultradia.iu.components.candle_render import OpcionesGrafico, dibujar_velas, texto_de_vela
from simultradia.services.grafico_service import DatosGrafico, GraficoService


def _datos(n=120, volumen=True):
    base = datetime(2026, 10, 1, tzinfo=timezone.utc)
    velas = [Vela(base + timedelta(hours=i), Decimal(100 + i % 9), Decimal(105 + i % 9), Decimal(95 + i % 9),
                  Decimal(102 + i % 9) if i % 2 else Decimal(98 + i % 9),
                  Decimal(1000 + i) if volumen else Decimal(0)) for i in range(n)]
    return GraficoService._con_indicadores(velas)


class PruebasDibujo(unittest.TestCase):
    def _png(self, figura):
        buffer = io.BytesIO()
        figura.savefig(buffer, format="png")
        return buffer.getvalue()

    def test_dibuja_velas_con_los_indicadores_por_defecto(self):
        figura = Figure()
        dibujo = dibujar_velas(figura, _datos(), IntervaloVela.H1, OpcionesGrafico(visibles=60))
        self.assertEqual(len(dibujo.velas), 60)
        self.assertEqual(len(figura.axes), 2)               # precio + volumen
        self.assertTrue(self._png(figura).startswith(b"\x89PNG"))

    def test_cada_panel_inferior_aparece_solo_si_se_pide(self):
        casos = [(OpcionesGrafico(volumen=False), 1), (OpcionesGrafico(volumen=True), 2),
                 (OpcionesGrafico(volumen=False, rsi=True), 2), (OpcionesGrafico(volumen=False, macd=True), 2),
                 (OpcionesGrafico(volumen=True, rsi=True, macd=True), 4)]
        for opciones, paneles in casos:
            with self.subTest(opciones=opciones):
                figura = Figure()
                dibujar_velas(figura, _datos(), IntervaloVela.H1, opciones)
                self.assertEqual(len(figura.axes), paneles)
                self.assertTrue(self._png(figura))

    def test_todos_los_indicadores_a_la_vez(self):
        figura = Figure()
        opciones = OpcionesGrafico(visibles=500, sma=True, ema=True, bollinger=True, volumen=True, rsi=True, macd=True)
        dibujo = dibujar_velas(figura, _datos(), IntervaloVela.D1, opciones)
        self.assertEqual(len(dibujo.velas), 120)             # pide más velas de las que hay
        self.assertTrue(self._png(figura))

    def test_sin_volumen_en_los_datos_no_se_dibuja_su_panel(self):
        figura = Figure()
        dibujar_velas(figura, _datos(volumen=False), IntervaloVela.D1, OpcionesGrafico(volumen=True))
        self.assertEqual(len(figura.axes), 1)                # divisas e índices no informan volumen

    def test_pocas_velas_para_los_indicadores_no_rompe_el_dibujo(self):
        figura = Figure()
        dibujar_velas(figura, _datos(10), IntervaloVela.H1,
                      OpcionesGrafico(bollinger=True, rsi=True, macd=True))
        self.assertTrue(self._png(figura))

    def test_sin_velas_muestra_un_aviso_y_no_falla(self):
        figura = Figure()
        vacio = GraficoService._con_indicadores([])
        self.assertIsNone(dibujar_velas(figura, vacio, IntervaloVela.H1))
        self.assertIsNone(dibujar_velas(figura, None, IntervaloVela.H1))
        self.assertTrue(self._png(figura))

    def test_se_puede_redibujar_muchas_veces_sobre_la_misma_figura(self):
        figura = Figure()
        for visibles in (120, 60, 30, 120):
            dibujar_velas(figura, _datos(), IntervaloVela.H4, OpcionesGrafico(visibles=visibles, rsi=True))
        self.assertEqual(len(figura.axes), 3)

    def test_texto_de_la_vela(self):
        texto = texto_de_vela(_datos(2).velas[1])
        self.assertTrue(all(letra in texto for letra in ("O ", "H ", "L ", "C ", "Vol")))


if __name__ == "__main__":
    unittest.main()
