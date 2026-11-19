"""Pruebas de la curva de capital: se dibuja de verdad (matplotlib, sin ventana) y el eje horizontal dice hora o fecha."""
import io
import re
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

from matplotlib.figure import Figure

from simultradia.analisis.metricas import caidas
from simultradia.domain.entities.snapshot_entity import SnapshotPortafolio
from simultradia.iu.components.equity_render import (
    dibujar_curva, etiquetas_eje_x, marcas_eje_x, texto_de_punto)

INICIO = datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)


def _puntos(n=72, paso=timedelta(hours=1)):
    resultado = []
    for i in range(n):
        patrimonio = D(10000 + (i * 7) % 90 - (i % 5) * 20)
        resultado.append(SnapshotPortafolio(1, INICIO + paso * i, patrimonio - 500, D("500"), patrimonio))
    return resultado


def _dibujar(puntos, horas=None, capital=D("10000")):
    figura = Figure()
    valores = [float(p.patrimonio_total) for p in puntos]
    dibujo = dibujar_curva(figura, puntos, caidas(valores), capital, horas)
    return figura, dibujo


class PruebasDibujo(unittest.TestCase):
    def _png(self, figura):
        buffer = io.BytesIO()
        figura.savefig(buffer, format="png")
        return buffer.getvalue()

    def test_dibuja_la_curva_y_la_caida(self):
        figura, dibujo = _dibujar(_puntos())
        self.assertEqual(len(figura.axes), 2)                      # patrimonio + caída
        self.assertEqual(len(dibujo.puntos), 72)
        self.assertTrue(self._png(figura).startswith(b"\x89PNG"))

    def test_el_rango_muestra_solo_las_ultimas_horas(self):
        _, dibujo = _dibujar(_puntos(72), horas=24)
        self.assertEqual(len(dibujo.puntos), 25)                   # las de las últimas 24 h, ambos extremos
        _, dibujo = _dibujar(_puntos(72), horas=None)
        self.assertEqual(len(dibujo.puntos), 72)

    def test_un_rango_mas_corto_que_el_historial_deja_al_menos_dos_puntos(self):
        _, dibujo = _dibujar(_puntos(3, paso=timedelta(days=2)), horas=1)
        self.assertEqual(len(dibujo.puntos), 2)

    def test_el_eje_horizontal_lleva_etiquetas_de_hora(self):
        figura, _ = _dibujar(_puntos(30))
        textos = [t.get_text() for t in figura.axes[1].get_xticklabels()]
        self.assertTrue(len(textos) >= 4)
        self.assertTrue(all(re.match(r"^\d\d:\d\d", t) for t in textos))

    def test_las_etiquetas_del_eje_horizontal_salen_bajo_la_curva_y_bajo_la_caida(self):
        figura, _ = _dibujar(_puntos(30))
        for ejes in figura.axes:
            self.assertTrue(ejes.xaxis.get_tick_params(which="major")["labelbottom"])
        self.assertEqual([t.get_text() for t in figura.axes[0].get_xticklabels()],
                         [t.get_text() for t in figura.axes[1].get_xticklabels()])

    def test_el_eje_horizontal_lleva_fechas_con_historiales_largos(self):
        figura, _ = _dibujar(_puntos(60, paso=timedelta(days=1)))
        textos = [t.get_text() for t in figura.axes[1].get_xticklabels()]
        self.assertTrue(all(re.match(r"^\d{1,2} [a-z]{3}", t) for t in textos))

    def test_con_menos_de_dos_puntos_muestra_un_aviso_y_no_falla(self):
        for puntos in ([], _puntos(1), None):
            figura = Figure()
            self.assertIsNone(dibujar_curva(figura, puntos, [], D("10000")))
            self.assertTrue(self._png(figura))

    def test_la_escala_se_ajusta_a_lo_que_se_ve_y_no_empieza_en_cero(self):
        # patrimonio entre ~9 900 y ~10 100; el capital inicial (1 000) queda muy lejos: no debe estirar el eje
        figura, _ = _dibujar(_puntos(72), capital=D("1000"))
        inferior, superior = figura.axes[0].get_ylim()
        self.assertGreater(inferior, 9000)
        self.assertLess(superior, 11000)
        self.assertFalse(any(len(set(l.get_ydata())) == 1 and l.get_ydata()[0] == 1000 for l in figura.axes[0].lines))

    def test_el_capital_inicial_se_dibuja_solo_si_cae_dentro_de_la_escala(self):
        puntos = _puntos(72)
        dentro = (min(float(p.patrimonio_total) for p in puntos) + max(float(p.patrimonio_total) for p in puntos)) / 2
        figura, _ = _dibujar(puntos, capital=D(str(dentro)))
        self.assertTrue(any(len(set(l.get_ydata())) == 1 and abs(l.get_ydata()[0] - dentro) < 1e-6
                            for l in figura.axes[0].lines))

    def test_una_curva_sin_variacion_igual_tiene_escala(self):
        puntos = [SnapshotPortafolio(1, INICIO + timedelta(hours=i), D(500), D(500), D(1000)) for i in range(5)]
        figura, _ = _dibujar(puntos)
        inferior, superior = figura.axes[0].get_ylim()
        self.assertTrue(inferior < 1000 < superior)

    def test_por_debajo_del_capital_inicial_tambien_dibuja(self):
        figura, _ = _dibujar(_puntos(10), capital=D("20000"))
        self.assertTrue(self._png(figura))

    def test_se_puede_redibujar_muchas_veces_sobre_la_misma_figura(self):
        figura, puntos = Figure(), _puntos(48)
        valores = [float(p.patrimonio_total) for p in puntos]
        for horas in (None, 24, 6, None):
            dibujar_curva(figura, puntos, caidas(valores), D("10000"), horas)
        self.assertEqual(len(figura.axes), 2)

    def test_el_texto_del_punto_lleva_fecha_hora_y_cifras(self):
        texto = texto_de_punto(_puntos(1)[0])
        self.assertRegex(texto, r"^\d\d/\d\d/2026 \d\d:\d\d   Patrimonio ")
        self.assertTrue(all(palabra in texto for palabra in ("Saldo", "Posiciones")))


class PruebasEjeX(unittest.TestCase):
    def test_un_dia_da_marcas_de_hora_y_la_fecha_solo_al_cambiar_de_dia(self):
        marcas = marcas_eje_x(INICIO + timedelta(hours=3), INICIO + timedelta(hours=27))
        etiquetas = etiquetas_eje_x(marcas)
        dias = [m.astimezone().date() for m in marcas]
        for etiqueta, dia, anterior in zip(etiquetas, dias, [None] + dias[:-1]):
            self.assertRegex(etiqueta.split("\n")[0], r"^\d\d:\d\d$")
            self.assertEqual("\n" in etiqueta, anterior is None or dia != anterior)

    def test_las_marcas_caen_en_horas_redondas_y_dentro_del_rango(self):
        inicio, fin = INICIO + timedelta(minutes=20), INICIO + timedelta(hours=30, minutes=40)
        marcas = marcas_eje_x(inicio, fin)
        self.assertTrue(all(inicio <= m <= fin for m in marcas))
        self.assertTrue(all((m.minute, m.second) == (0, 0) for m in marcas))
        self.assertTrue(2 <= len(marcas) <= 9)

    def test_semanas_o_meses_dan_fechas_y_el_ano_solo_al_cambiar(self):
        marcas = marcas_eje_x(datetime(2026, 12, 20, tzinfo=timezone.utc), datetime(2027, 2, 10, tzinfo=timezone.utc))
        etiquetas = etiquetas_eje_x(marcas)
        self.assertRegex(etiquetas[0], r"^\d{1,2} [a-z]{3}\n\d{4}$")           # la primera lleva el año
        con_ano = [e for e in etiquetas if "\n" in e]
        self.assertEqual(len(con_ano), 2)                                       # la primera y la del cambio de año
        self.assertTrue(con_ano[1].endswith("2027"))

    def test_un_rato_muy_corto_igual_tiene_marcas_repartidas(self):
        marcas = marcas_eje_x(INICIO + timedelta(minutes=5), INICIO + timedelta(minutes=45))
        self.assertGreaterEqual(len(marcas), 2)
        self.assertTrue(all(re.match(r"^\d\d:\d\d", e) for e in etiquetas_eje_x(marcas)))


if __name__ == "__main__":
    unittest.main()
