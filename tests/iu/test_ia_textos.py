"""Pruebas de los textos de la pantalla de volatilidad (Python puro)."""
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal

from simultradia.domain.entities.prediccion_volatilidad_entity import PrediccionVolatilidad
from simultradia.domain.enums import NivelVolatilidad as N
from simultradia.analisis.volatilidad import NOMBRES_FEATURES
from simultradia.iu.ia import textos

_AHORA = datetime(2026, 11, 18, tzinfo=timezone.utc)


def _p(**cambios):
    datos = dict(id_activo=1, id_modelo=1, generada_en=_AHORA, fecha_objetivo=_AHORA, precio_referencia=Decimal(100),
                 rango_predicho=0.023, rango_bajo=0.016, rango_alto=0.033, rango_hoy=0.03, rango_normal=0.02,
                 umbral_bajo=0.012, umbral_alto=0.026, nivel=N.NORMAL)
    datos.update(cambios)
    return PrediccionVolatilidad(**datos)


class PruebasTextos(unittest.TestCase):
    def test_numeros_con_coma_decimal(self):
        self.assertEqual(textos.pct(0.543), "54 %")
        self.assertEqual(textos.rango(0.023), "2,3 %")
        self.assertEqual(textos.numero(1.5, 2, con_signo=True), "+1,50")
        self.assertEqual(textos.veces(1.44), "1,4× lo normal")

    def test_error_en_porcentaje_del_rango(self):
        self.assertEqual(textos.error_pct(0.0), "±0 %")
        self.assertEqual(textos.error_pct(0.405465), "±50 %")

    def test_cada_feature_tiene_nombre_legible(self):
        for nombre in NOMBRES_FEATURES:
            self.assertNotEqual(textos.factor(nombre), nombre)
        self.assertEqual(textos.factor("desconocida"), "desconocida")

    def test_niveles_y_frases(self):
        self.assertEqual(textos.nivel(N.ALTA), "Alta")
        for n in N:
            self.assertTrue(textos.frase_percentil(n))
        self.assertEqual(textos.titulo_nivel(N.ALTA), "AGITADO")
        self.assertIn("3 de cada 4", textos.frase_percentil(N.ALTA))
        self.assertNotIn("75", textos.frase_percentil(N.ALTA))

    def test_filtros_y_conteos_del_escaner(self):
        class S:
            def __init__(self, n):
                self.prediccion = _p(nivel=n)
        senales = [S(N.ALTA), S(N.ALTA), S(N.NORMAL), S(N.BAJA)]
        self.assertEqual(textos.conteos(senales), {"todos": 4, "alta": 2, "normal": 1, "baja": 1})
        self.assertEqual(len(textos.filtrar(senales, "todos")), 4)
        self.assertEqual(len(textos.filtrar(senales, "alta")), 2)
        self.assertEqual(textos.filtrar(senales, "baja")[0].prediccion.nivel, N.BAJA)
        self.assertEqual([textos.etiqueta_nivel(n) for n in N], ["calma", "", "alerta"]
                         if list(N) == [N.BAJA, N.NORMAL, N.ALTA] else [textos.etiqueta_nivel(n) for n in N])

    def test_frases_de_la_pestana_volatilidad(self):
        p = _p(rango_hoy=0.03, rango_predicho=0.023)
        self.assertIn("1,5× lo normal", textos.frase_hoy(p))
        self.assertIn("menos", textos.frase_hoy(p))
        self.assertIn("1,2 %", textos.texto_umbrales(p))
        self.assertIn("2,6 %", textos.texto_umbrales(p))
        self.assertIn("2,3 %", textos.uso_tamano(p))
        self.assertIn("No dice si sube o baja", textos.uso_direccion())

    def test_registro_diferencia_niveles_y_error(self):
        self.assertEqual(textos.diferencia_pp(_p()), "—")
        self.assertEqual(textos.diferencia_pp(_p(rango_real=0.026)), "+0,3 pp")
        self.assertEqual(textos.niveles(_p(nivel=N.ALTA, nivel_real=N.NORMAL)), "Alta → Normal")
        self.assertEqual(textos.niveles(_p()), "Normal → —")
        self.assertEqual(textos.error_contra_hoy(0.21), "−21 %")
        self.assertEqual(textos.error_contra_hoy(-0.1), "+10 %")
        self.assertEqual(textos.error_contra_hoy(None), "—")

    def test_ejemplo_del_error(self):
        self.assertIn("2,0 %", textos.ejemplo_error(0.405465))
        self.assertIn("±50 %", textos.ejemplo_error(0.405465))
        self.assertAlmostEqual(textos.siempre_normal(), 0.5)

    def test_resultado_del_registro(self):
        self.assertEqual(textos.resultado(_p()), "Pendiente")
        self.assertEqual(textos.etiqueta_resultado(_p()), "")
        self.assertEqual(textos.resultado(_p(acierto_nivel=True)), "Acertó")
        self.assertEqual(textos.etiqueta_resultado(_p(acierto_nivel=False)), "baja")

    def test_periodo(self):
        self.assertEqual(textos.periodo(date(2019, 3, 1).toordinal(), date(2020, 8, 1).toordinal()), "mar 2019 – ago 2020")

    def test_las_frases_dicen_los_numeros_de_la_prediccion(self):
        p = _p()
        self.assertIn("1,6 %", textos.frase_intervalo(p))
        self.assertIn("3,3 %", textos.frase_intervalo(p))
        self.assertIn("1,1× lo normal", textos.frase_normal(p))

    def test_entidad_error_y_veces(self):
        p = _p(rango_real=0.023)
        self.assertAlmostEqual(p.error, 0.0)
        self.assertTrue(p.dentro_del_intervalo)
        self.assertAlmostEqual(_p().veces_lo_normal, 1.15)


if __name__ == "__main__":
    unittest.main()
