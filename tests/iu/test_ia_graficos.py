"""Prueba que los gráficos de la pantalla de IA se dibujan de verdad (matplotlib, sin ventana)."""
import io
import unittest

from matplotlib.figure import Figure

from simultradia.analisis.montecarlo import proyectar
from simultradia.ia.entrenamiento import Evaluacion, Tramo
from simultradia.iu.ia.graficos import dibujar_proyeccion, dibujar_tramos


def _png(figura):
    buffer = io.BytesIO()
    figura.savefig(buffer, format="png")
    return buffer.getvalue()


class PruebasGraficosIA(unittest.TestCase):
    def test_proyeccion_con_y_sin_nivel(self):
        cierres = [100 + i % 7 + i * 0.05 for i in range(300)]
        proyeccion = proyectar(cierres, 5, 500, semilla=1)
        for nivel in (None, 98.5):
            figura = Figure()
            dibujar_proyeccion(figura, proyeccion, nivel)
            self.assertTrue(_png(figura).startswith(b"\x89PNG"))

    def test_sin_datos_dibuja_un_aviso_en_lugar_de_fallar(self):
        for dibujar in (dibujar_proyeccion, dibujar_tramos):
            figura = Figure()
            dibujar(figura, None)
            self.assertTrue(_png(figura).startswith(b"\x89PNG"))

    def test_tramos(self):
        ev = Evaluacion(5, 100, 50, 10.0, 0.5, 0.4, 2.0, None,
                        tramos=[Tramo(1, 2, 10, 0.5, 0.4), Tramo(3, 4, 10, 0.45, 0.42)])
        figura = Figure()
        dibujar_tramos(figura, ev)
        self.assertEqual(len(figura.axes), 1)
        self.assertTrue(_png(figura).startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main()
