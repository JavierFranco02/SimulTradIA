"""Prueba que los gráficos de volatilidad se dibujan de verdad (matplotlib, sin ventana)."""
import io
import unittest
from datetime import timedelta
from decimal import Decimal

from matplotlib.figure import Figure

from simultradia.analisis.montecarlo import proyectar
from simultradia.domain.entities.prediccion_volatilidad_entity import PrediccionVolatilidad
from simultradia.domain.enums import NivelVolatilidad
from simultradia.ia.volatilidad import armar_dataset, entrenar
from simultradia.iu.ia.graficos import dibujar_historial, dibujar_proyeccion, dibujar_tramos
from tests.ia.vol_fakes import AHORA, crear_modelo_prueba, velas_vol


def _png(figura):
    buffer = io.BytesIO()
    figura.savefig(buffer, format="png")
    return buffer.getvalue()


class PruebasGraficosIA(unittest.TestCase):
    def test_proyeccion_con_y_sin_nivel(self):
        proyeccion = proyectar([100 + i % 7 + i * 0.05 for i in range(300)], 5, 500, semilla=1)
        for nivel in (None, 98.5):
            figura = Figure()
            dibujar_proyeccion(figura, proyeccion, nivel)
            self.assertTrue(_png(figura).startswith(b"\x89PNG"))

    def test_sin_datos_dibuja_un_aviso_en_lugar_de_fallar(self):
        for dibujar, vacio in ((dibujar_proyeccion, None), (dibujar_tramos, None), (dibujar_historial, [])):
            figura = Figure()
            dibujar(figura, vacio)
            self.assertTrue(_png(figura).startswith(b"\x89PNG"))

    def test_tramos(self):
        ev = entrenar(armar_dataset({i: velas_vol(700, i) for i in (1, 2)}), crear_modelo_prueba).evaluacion
        figura = Figure()
        dibujar_tramos(figura, ev)
        self.assertEqual(len(figura.axes), 1)
        self.assertTrue(_png(figura).startswith(b"\x89PNG"))

    def test_historial_con_pendientes_y_evaluadas(self):
        historial = [PrediccionVolatilidad(1, 1, AHORA - timedelta(days=i), AHORA, Decimal(100), 0.02, 0.015, 0.03,
                                           0.02, 0.02, 0.01, 0.03, NivelVolatilidad.NORMAL,
                                           rango_real=None if i == 0 else 0.025) for i in range(10)]
        figura = Figure()
        dibujar_historial(figura, historial)
        self.assertTrue(_png(figura).startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main()
