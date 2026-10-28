"""Pruebas del formato de números y fechas en pantalla."""
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from simultradia.iu.formato import compacto, dinero, hace, porcentaje, precio

E = "\u00a0"


class PruebasFormato(unittest.TestCase):
    def test_dinero_usa_espacio_de_miles_y_coma_decimal(self):
        self.assertEqual(dinero(Decimal("10000")), "10%s000,00%sUSD" % (E, E))
        self.assertEqual(dinero(Decimal("1234567.5"), "EUR"), "1%s234%s567,50%sEUR" % (E, E, E))

    def test_signo_solo_cuando_se_pide(self):
        self.assertEqual(dinero(Decimal("250"), con_signo=True), "+250,00%sUSD" % E)
        self.assertEqual(dinero(Decimal("250")), "250,00%sUSD" % E)
        self.assertEqual(dinero(Decimal("-250"), con_signo=True), "-250,00%sUSD" % E)

    def test_cero_lleva_mas_y_un_negativo_minimo_no_se_muestra_como_menos_cero(self):
        self.assertEqual(porcentaje(Decimal("0"), con_signo=True), "+0,00%s%%" % E)
        self.assertEqual(porcentaje(Decimal("0.001"), con_signo=True), "+0,00%s%%" % E)

    def test_porcentaje(self):
        self.assertEqual(porcentaje(Decimal("2.5"), con_signo=True), "+2,50%s%%" % E)
        self.assertEqual(porcentaje(Decimal("-10")), "-10,00%s%%" % E)

    def test_el_precio_usa_mas_decimales_cuanto_mas_barato_es(self):
        self.assertEqual(precio(Decimal("67123.456")), "67%s123,46" % E)
        self.assertEqual(precio(Decimal("3.456789")), "3,4568")
        self.assertEqual(precio(Decimal("0.1234567")), "0,123457")

    def test_numeros_grandes_abreviados(self):
        self.assertEqual(compacto(Decimal("950")), "950")
        self.assertEqual(compacto(Decimal("12400")), "12,40%sK" % E)
        self.assertEqual(compacto(Decimal("1250000")), "1,25%sM" % E)
        self.assertEqual(compacto(Decimal("3400000000")), "3,40%sB" % E)

    def test_hace(self):
        ahora = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
        self.assertEqual(hace(ahora - timedelta(seconds=5), ahora), "hace 5 s")
        self.assertEqual(hace(ahora - timedelta(minutes=3), ahora), "hace 3 min")
        self.assertEqual(hace(ahora - timedelta(hours=2), ahora), "hace 2 h")
        self.assertEqual(hace(ahora - timedelta(days=4), ahora), "hace 4 d")
        self.assertEqual(hace(ahora + timedelta(seconds=3), ahora), "hace 0 s")
        self.assertEqual(hace(None), "—")


if __name__ == "__main__":
    unittest.main()
