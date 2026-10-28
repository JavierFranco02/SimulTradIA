"""Pruebas del servicio del gráfico."""
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

from simultradia.domain.entities.cotizacion_entity import Cotizacion
from simultradia.domain.entities.vela_entity import Vela
from simultradia.domain.enums import IntervaloVela as I
from simultradia.domain.enums import TipoActivo
from simultradia.services.grafico_service import GraficoService
from tests.fakes import DatabaseFalsa, RepoPrecioFalso

INICIO = datetime(2026, 10, 20, 0, 0, tzinfo=timezone.utc)


def _horas(n):
    return [Vela(INICIO + timedelta(hours=i), D(i + 1), D(i + 2), D(i), D(i + 1), D(10)) for i in range(n)]


class PruebasGraficoService(unittest.TestCase):
    def setUp(self):
        self.precios = RepoPrecioFalso()
        self.precios.velas[(1, I.H1)] = _horas(100)
        self.servicio = GraficoService(DatabaseFalsa(), self.precios)

    def test_lee_las_velas_guardadas_y_calcula_todos_los_indicadores(self):
        datos = self.servicio.obtener_datos(1, I.H1)
        self.assertEqual(len(datos.velas), 100)
        for serie in (datos.sma, datos.ema, datos.bb_media, datos.bb_superior, datos.bb_inferior,
                      datos.rsi, datos.macd, datos.macd_senal, datos.macd_hist):
            self.assertEqual(len(serie), 100)
        self.assertIsNone(datos.sma[18])
        self.assertIsNotNone(datos.sma[19])
        self.assertGreater(datos.bb_superior[-1], datos.bb_inferior[-1])
        self.assertEqual(datos.rsi[-1], 100.0)           # la serie solo sube

    def test_4h_se_arma_agrupando_las_velas_de_1h(self):
        datos = self.servicio.obtener_datos(1, I.H4)
        self.assertEqual(len(datos.velas), 25)
        self.assertEqual(datos.velas[0].volumen, D("40"))

    def test_sin_velas_guardadas_devuelve_todo_vacio(self):
        datos = self.servicio.obtener_datos(99, I.D1)
        self.assertEqual((datos.velas, datos.sma, datos.rsi, datos.macd_hist), ([], [], [], []))

    def test_el_precio_en_vivo_actualiza_la_ultima_vela_y_los_indicadores(self):
        datos = self.servicio.obtener_datos(1, I.H1)
        ultima = datos.velas[-1]
        cot = Cotizacion(precio=D("500"), id_activo=1, actualizado_en=ultima.momento + timedelta(minutes=10))
        nuevos = self.servicio.con_precio(datos, cot, I.H1, TipoActivo.CRIPTO)
        self.assertEqual(len(nuevos.velas), 100)
        self.assertEqual((nuevos.velas[-1].cierre, nuevos.velas[-1].maximo), (D("500"), D("500")))
        self.assertGreater(nuevos.sma[-1], datos.sma[-1])
        self.assertEqual(datos.velas[-1].cierre, ultima.cierre)   # el original no cambió

    def test_la_cripto_abre_una_vela_nueva_cuando_empieza_otra_hora(self):
        datos = self.servicio.obtener_datos(1, I.H1)
        cot = Cotizacion(precio=D("7"), id_activo=1,
                         actualizado_en=datos.velas[-1].momento + timedelta(hours=1, minutes=1))
        self.assertEqual(len(self.servicio.con_precio(datos, cot, I.H1, TipoActivo.CRIPTO).velas), 101)

    def test_una_accion_no_abre_velas_nuevas_con_el_mercado_cerrado(self):
        datos = self.servicio.obtener_datos(1, I.H1)
        cot = Cotizacion(precio=D("7"), id_activo=1,
                         actualizado_en=datos.velas[-1].momento + timedelta(hours=40))
        self.assertEqual(len(self.servicio.con_precio(datos, cot, I.H1, TipoActivo.ACCION).velas), 100)


if __name__ == "__main__":
    unittest.main()
