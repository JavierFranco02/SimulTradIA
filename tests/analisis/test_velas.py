"""Pruebas de agrupar velas y aplicar el precio en vivo."""
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

from simultradia.analisis.velas import agrupar_velas, aplicar_precio, inicio_de_periodo
from simultradia.domain.entities.vela_entity import Vela
from simultradia.domain.enums import IntervaloVela as I


def _utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


def _vela(momento, a, h, l, c, v="1"):
    return Vela(momento, D(a), D(h), D(l), D(c), D(v))


class PruebasInicioDePeriodo(unittest.TestCase):
    def test_cada_intervalo_empieza_en_su_multiplo(self):
        momento = _utc(2026, 10, 25, 14, 37, 12)    # un domingo
        self.assertEqual(inicio_de_periodo(momento, I.M15), _utc(2026, 10, 25, 14, 30))
        self.assertEqual(inicio_de_periodo(momento, I.H1), _utc(2026, 10, 25, 14, 0))
        self.assertEqual(inicio_de_periodo(momento, I.H4), _utc(2026, 10, 25, 12, 0))
        self.assertEqual(inicio_de_periodo(momento, I.D1), _utc(2026, 10, 25))

    def test_la_semana_empieza_el_lunes(self):
        self.assertEqual(inicio_de_periodo(_utc(2026, 10, 25, 23, 59), I.W1), _utc(2026, 10, 19))
        self.assertEqual(inicio_de_periodo(_utc(2026, 10, 19, 0, 0), I.W1), _utc(2026, 10, 19))


class PruebasAgruparVelas(unittest.TestCase):
    def test_cuatro_velas_de_una_hora_forman_una_de_cuatro(self):
        base = _utc(2026, 10, 25, 12)
        horas = [_vela(base + timedelta(hours=i), a, h, l, c, "10")
                 for i, (a, h, l, c) in enumerate([("10", "12", "9", "11"), ("11", "15", "10", "14"),
                                                   ("14", "14", "8", "9"), ("9", "13", "9", "12")])]
        [grupo] = agrupar_velas(horas, I.H4)
        self.assertEqual((grupo.momento, grupo.apertura, grupo.maximo, grupo.minimo, grupo.cierre),
                         (base, D("10"), D("15"), D("8"), D("12")))
        self.assertEqual(grupo.volumen, D("40"))

    def test_velas_de_periodos_distintos_quedan_separadas(self):
        velas = [_vela(_utc(2026, 10, 25, 11), "1", "1", "1", "1"),
                 _vela(_utc(2026, 10, 25, 12), "2", "2", "2", "2")]
        self.assertEqual([g.momento.hour for g in agrupar_velas(velas, I.H4)], [8, 12])

    def test_dias_a_semana(self):
        lunes = _utc(2026, 10, 19)
        dias = [_vela(lunes + timedelta(days=i), "1", str(i + 2), "1", "1") for i in range(9)]
        semanas = agrupar_velas(dias, I.W1)
        self.assertEqual([s.momento for s in semanas], [lunes, lunes + timedelta(days=7)])
        self.assertEqual(semanas[0].maximo, D("8"))


class PruebasAplicarPrecio(unittest.TestCase):
    def setUp(self):
        self.velas = [_vela(_utc(2026, 10, 25, 13), "10", "12", "9", "11"),
                      _vela(_utc(2026, 10, 25, 14), "11", "13", "10", "12", "5")]

    def test_dentro_de_la_ultima_vela_cambia_el_cierre_y_amplia_extremos(self):
        nuevas = aplicar_precio(self.velas, D("14"), _utc(2026, 10, 25, 14, 20), I.H1)
        self.assertEqual(len(nuevas), 2)
        ultima = nuevas[-1]
        self.assertEqual((ultima.apertura, ultima.maximo, ultima.minimo, ultima.cierre),
                         (D("11"), D("14"), D("10"), D("14")))
        self.assertEqual(ultima.volumen, D("5"))
        nuevas = aplicar_precio(nuevas, D("7"), _utc(2026, 10, 25, 14, 40), I.H1)
        self.assertEqual((nuevas[-1].minimo, nuevas[-1].cierre), (D("7"), D("7")))

    def test_no_modifica_la_lista_original(self):
        aplicar_precio(self.velas, D("99"), _utc(2026, 10, 25, 14, 20), I.H1)
        self.assertEqual(self.velas[-1].cierre, D("12"))

    def test_un_periodo_nuevo_abre_una_vela_nueva(self):
        nuevas = aplicar_precio(self.velas, D("13.5"), _utc(2026, 10, 25, 15, 1), I.H1)
        self.assertEqual(len(nuevas), 3)
        self.assertEqual(nuevas[-1].momento, _utc(2026, 10, 25, 15))
        self.assertEqual({nuevas[-1].apertura, nuevas[-1].maximo, nuevas[-1].minimo, nuevas[-1].cierre},
                         {D("13.5")})

    def test_un_precio_mas_viejo_que_la_ultima_vela_se_ignora(self):
        self.assertEqual(aplicar_precio(self.velas, D("1"), _utc(2026, 10, 25, 9), I.H1), self.velas)

    def test_sin_abrir_nuevas_un_precio_fuera_de_la_vela_no_dibuja_velas_planas(self):
        # Mercado cerrado (fin de semana): el precio de ahora no pertenece a ninguna vela guardada.
        nuevas = aplicar_precio(self.velas, D("13.5"), _utc(2026, 10, 25, 15, 1), I.H1, abrir_nuevas=False)
        self.assertEqual(nuevas, self.velas)

    def test_una_vela_desalineada_de_la_bolsa_tambien_se_actualiza(self):
        # Las velas de 1 h de las acciones empiezan a las :30; el precio de las 14:10 está en la de las 13:30.
        velas = [_vela(_utc(2026, 10, 23, 13, 30), "10", "12", "9", "11")]
        nuevas = aplicar_precio(velas, D("15"), _utc(2026, 10, 23, 14, 10), I.H1, abrir_nuevas=False)
        self.assertEqual((len(nuevas), nuevas[-1].cierre, nuevas[-1].maximo), (1, D("15"), D("15")))

    def test_sin_velas_no_hace_nada(self):
        self.assertEqual(aplicar_precio([], D("1"), _utc(2026, 10, 25), I.H1), [])


if __name__ == "__main__":
    unittest.main()
