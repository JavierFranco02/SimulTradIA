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
from simultradia.iu.ia.graficos import (dibujar_calibracion, dibujar_historial, dibujar_proyeccion, dibujar_tramos,
                                       dibujar_ultimos_dias)
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
                                           rango_real=None if i == 0 else (0.04 if i == 1 else 0.025))
                     for i in range(10)]
        figura = Figure()
        dibujar_historial(figura, historial)
        self.assertEqual(len(figura.axes), 1)
        self.assertEqual(len(figura.axes[0].patches), 10)      # una banda por predicción, también la pendiente
        self.assertTrue(_png(figura).startswith(b"\x89PNG"))

    def test_historial_se_dibuja_desde_la_primera_prediccion_aunque_este_pendiente(self):
        def prediccion(i, real):
            return PrediccionVolatilidad(1, 1, AHORA - timedelta(days=i), AHORA, Decimal(100), 0.02, 0.015, 0.03,
                                         0.02, 0.02, 0.01, 0.03, NivelVolatilidad.NORMAL, rango_real=real)
        for historial in ([prediccion(0, None)], [prediccion(0, None), prediccion(1, None)], [prediccion(0, 0.02)]):
            figura = Figure()
            dibujar_historial(figura, historial)
            self.assertEqual(len(figura.axes), 1)
            self.assertEqual(len(figura.axes[0].patches), len(historial))
            self.assertTrue(_png(figura).startswith(b"\x89PNG"))

    def test_historial_el_punto_real_cabe_en_el_eje_y_las_marcas_no_se_repiten(self):
        def prediccion(i, predicho, bajo, alto, real):
            return PrediccionVolatilidad(1, 1, AHORA - timedelta(days=i), AHORA, Decimal(100), predicho, bajo, alto,
                                         predicho, predicho, bajo, alto, NivelVolatilidad.NORMAL, rango_real=real)
        # real (11,4 %) por encima de la banda: el techo del eje debe incluirlo
        figura = Figure()
        dibujar_historial(figura, [prediccion(1, 0.057, 0.04, 0.08, 0.114), prediccion(0, 0.055, 0.04, 0.08, 0.029)])
        self.assertGreater(figura.axes[0].get_ylim()[1], 11.4)
        # rangos muy chicos (0,1 %): las marcas del eje llevan los decimales que hagan falta y no se repiten
        figura = Figure()
        dibujar_historial(figura, [prediccion(1, 0.001, 0.0005, 0.0015, 0.001), prediccion(0, 0.001, 0.0005, 0.0015, None)])
        _png(figura)
        etiquetas = [t.get_text() for t in figura.axes[0].get_yticklabels() if t.get_text()]
        self.assertEqual(len(etiquetas), len(set(etiquetas)))
        self.assertTrue(any("0,0" in e for e in etiquetas))

    def test_ultimos_dias_con_y_sin_prediccion(self):
        p = PrediccionVolatilidad(1, 1, AHORA, AHORA, Decimal(100), 0.02, 0.015, 0.03, 0.02, 0.02, 0.01, 0.03,
                                  NivelVolatilidad.ALTA)
        for prediccion in (p, None):
            figura = Figure()
            dibujar_ultimos_dias(figura, [0.01 + 0.0005 * i for i in range(30)], prediccion)
            self.assertTrue(_png(figura).startswith(b"\x89PNG"))
        figura = Figure()
        fechas = [(AHORA - timedelta(days=30 - i)).date() for i in range(30)]
        dibujar_ultimos_dias(figura, [0.01] * 30, p, fechas)
        self.assertEqual(figura.axes[0].get_xticklabels()[-1].get_text(), "mañana")
        self.assertTrue(_png(figura).startswith(b"\x89PNG"))
        figura = Figure()
        dibujar_ultimos_dias(figura, [], None)
        self.assertTrue(_png(figura).startswith(b"\x89PNG"))

    def test_calibracion(self):
        ev = entrenar(armar_dataset({i: velas_vol(700, i) for i in (1, 2)}), crear_modelo_prueba).evaluacion
        for grupos in (ev.calibracion, []):
            figura = Figure()
            dibujar_calibracion(figura, grupos)
            self.assertTrue(_png(figura).startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main()
