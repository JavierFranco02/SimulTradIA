"""Pruebas de los textos de la pantalla de IA."""
import unittest
from datetime import datetime, timezone
from decimal import Decimal

from simultradia.domain.entities.prediccion_entity import Prediccion
from simultradia.domain.enums import DireccionPrediccion as D
from simultradia.iu.ia import textos


def _p(acierto=None):
    return Prediccion(1, 1, 5, datetime(2026, 11, 18, tzinfo=timezone.utc), datetime(2026, 11, 25, tzinfo=timezone.utc),
                      D.ALCISTA, 0.5, 0.2, 0.3, 0.5, Decimal(100), acierto=acierto)


class PruebasTextos(unittest.TestCase):
    def test_porcentajes_y_numeros_en_espanol(self):
        self.assertEqual(textos.pct(0.543), "54 %")
        self.assertEqual(textos.pct(0.5432, 1), "54,3 %")
        self.assertEqual(textos.numero(2.4149), "2,41")
        self.assertEqual(textos.numero(3.14, 1, con_signo=True), "+3,1")

    def test_confianza_con_su_nivel(self):
        self.assertEqual(textos.confianza(0.40), "Baja · 40 %")
        self.assertTrue(textos.confianza(0.54).startswith("Media"))
        self.assertTrue(textos.confianza(0.72).startswith("Alta"))

    def test_color_de_fila_segun_direccion(self):
        self.assertEqual(textos.etiqueta_fila(D.ALCISTA), "alza")
        self.assertEqual(textos.etiqueta_fila(D.BAJISTA), "baja")
        self.assertEqual(textos.etiqueta_fila(D.LATERAL), "")

    def test_resultado_de_una_prediccion(self):
        self.assertEqual((textos.resultado(_p()), textos.etiqueta_resultado(_p())), ("Pendiente", ""))
        self.assertEqual((textos.resultado(_p(True)), textos.etiqueta_resultado(_p(True))), ("Acertó", "alza"))
        self.assertEqual((textos.resultado(_p(False)), textos.etiqueta_resultado(_p(False))), ("Falló", "baja"))

    def test_todos_los_factores_tienen_nombre_legible(self):
        from simultradia.analisis.features import NOMBRES_FEATURES
        for nombre in NOMBRES_FEATURES:
            self.assertNotEqual(textos.factor(nombre), nombre)
        self.assertEqual(textos.factor("otro"), "otro")

    def test_periodo_de_un_tramo(self):
        from datetime import date
        self.assertEqual(textos.periodo(date(2019, 3, 5).toordinal(), date(2020, 8, 30).toordinal()),
                         "mar 2019 – ago 2020")
        self.assertEqual(textos.periodo(date(2019, 3, 5).toordinal(), date(2019, 3, 30).toordinal()), "mar 2019")

    def test_frases_llanas(self):
        self.assertIn("poco", textos.frase_direccion(D.LATERAL, 1))
        self.assertIn("1 día", textos.frase_direccion(D.ALCISTA, 1))
        self.assertIn("5 días", textos.frase_direccion(D.BAJISTA, 5))
        self.assertIn("33\xa0%", textos.frase_confianza(0.59))
        self.assertEqual(textos.nombre_modelo(1, "v2"), "Modelo a 1 día · versión 2")

    def test_lectura_de_la_calibracion(self):
        from simultradia.ia.entrenamiento import BinCalibracion
        sube = [BinCalibracion("< 0.4", 100, 0.36, 0.37), BinCalibracion("≥ 0.7", 100, 0.8, 0.75)]
        self.assertTrue(textos.lectura_calibracion(sube).startswith("Sí"))
        self.assertTrue(textos.lectura_calibracion(sube[::-1]).startswith("No"))
        self.assertIn("suficientes", textos.lectura_calibracion([BinCalibracion("< 0.4", 5, 0.4, 0.4)]))

    def test_lectura_de_la_validacion(self):
        from simultradia.ia.entrenamiento import Evaluacion
        ev = Evaluacion(5, 100, 50, 10.0, 0.435, 0.413, 2.06, None)
        self.assertIn("no ser casualidad", textos.lectura_validacion(ev))
        ev = Evaluacion(5, 100, 50, 10.0, 0.415, 0.413, 0.2, None)
        self.assertIn("casualidad", textos.lectura_validacion(ev))
        self.assertIn("demasiado pequeña", textos.lectura_validacion(ev))


if __name__ == "__main__":
    unittest.main()
