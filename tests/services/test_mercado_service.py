"""Pruebas del servicio de Mercado: buscar, filtrar, ordenar y destacados."""
import unittest
from datetime import datetime, timezone
from decimal import Decimal as D

from simultradia.core.exceptions import ErrorOperacionInvalida
from simultradia.domain.entities.activo_entity import Activo
from simultradia.domain.entities.cotizacion_entity import Cotizacion
from simultradia.domain.enums import TipoActivo
from simultradia.services.mercado_service import MercadoService
from tests.fakes import DatabaseFalsa, RepoActivoFalso, RepoPrecioFalso

AHORA = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)


class PruebasMercadoService(unittest.TestCase):
    def setUp(self):
        precios = RepoPrecioFalso()
        activos = [Activo("BTC/USDT", "Bitcoin", id_activo=1), Activo("ETH/USDT", "Ethereum", id_activo=2),
                   Activo("SOL/USDT", "Solana", id_activo=3), Activo("AAPL", "Apple", tipo=TipoActivo.ACCION, id_activo=4),
                   Activo("OLD/USDT", "Viejo", activo=False, id_activo=5)]
        # id: (precio, variación %, volumen)
        for id_activo, (p, v, vol) in {1: ("60000", "1.5", "900"), 2: ("3000", "-2.0", "500"),
                                       3: ("150", "6.0", "700")}.items():
            precios.cotizaciones[id_activo] = Cotizacion(
                precio=D(p), id_activo=id_activo, variacion_pct_dia=D(v), volumen_dia=D(vol),
                actualizado_en=AHORA)
        self.servicio = MercadoService(DatabaseFalsa(), RepoActivoFalso(activos, precios))

    def _tickers(self, panel):
        return [i.activo.ticker for i in panel.items]

    def test_solo_muestra_activos_habilitados(self):
        self.assertNotIn("OLD/USDT", self._tickers(self.servicio.obtener_panel()))

    def test_orden_por_defecto_es_por_ticker(self):
        self.assertEqual(self._tickers(self.servicio.obtener_panel()),
                         ["AAPL", "BTC/USDT", "ETH/USDT", "SOL/USDT"])

    def test_buscar_por_ticker_o_nombre_sin_importar_mayusculas(self):
        self.assertEqual(self._tickers(self.servicio.obtener_panel(texto=" sol ")), ["SOL/USDT"])
        self.assertEqual(self._tickers(self.servicio.obtener_panel(texto="ETHER")), ["ETH/USDT"])

    def test_ganadores_y_perdedores(self):
        self.assertEqual(self._tickers(self.servicio.obtener_panel(filtro="ganadores", orden="variacion",
                                                                   descendente=True)),
                         ["SOL/USDT", "BTC/USDT"])
        self.assertEqual(self._tickers(self.servicio.obtener_panel(filtro="perdedores")), ["ETH/USDT"])

    def test_orden_numerico_deja_al_final_los_que_no_tienen_precio(self):
        panel = self.servicio.obtener_panel(orden="volumen", descendente=True)
        self.assertEqual(self._tickers(panel), ["BTC/USDT", "SOL/USDT", "ETH/USDT", "AAPL"])
        panel = self.servicio.obtener_panel(orden="volumen", descendente=False)
        self.assertEqual(self._tickers(panel), ["ETH/USDT", "SOL/USDT", "BTC/USDT", "AAPL"])

    def test_un_orden_desconocido_vuelve_al_ticker(self):
        self.assertEqual(self._tickers(self.servicio.obtener_panel(orden="inventado"))[0], "AAPL")

    def test_filtra_por_categoria(self):
        self.assertEqual(self._tickers(self.servicio.obtener_panel(tipo=TipoActivo.ACCION)), ["AAPL"])
        self.assertEqual(self._tickers(self.servicio.obtener_panel(tipo=TipoActivo.CRIPTO)),
                         ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
        self.assertEqual(self._tickers(self.servicio.obtener_panel(tipo=TipoActivo.BONO)), [])

    def test_la_categoria_se_combina_con_la_busqueda_y_la_pestana(self):
        # Criptos que contienen "o" y suben: Bitcoin (+1,5) y Solana (+6); Ethereum baja.
        panel = self.servicio.obtener_panel(texto="o", filtro="ganadores", orden="variacion",
                                            descendente=True, tipo=TipoActivo.CRIPTO)
        self.assertEqual(self._tickers(panel), ["SOL/USDT", "BTC/USDT"])

    def test_la_fecha_de_actualizacion_es_la_mas_reciente(self):
        self.assertEqual(self.servicio.obtener_panel().actualizado_en, AHORA)

    def test_sin_precios_no_hay_fecha_de_actualizacion(self):
        servicio = MercadoService(DatabaseFalsa(), RepoActivoFalso([Activo("BTC/USDT", "Bitcoin", id_activo=1)]))
        panel = servicio.obtener_panel()
        self.assertEqual((len(panel.items), panel.actualizado_en), (1, None))

    def test_ficha_de_un_activo(self):
        item = self.servicio.obtener_activo(1)
        self.assertEqual((item.activo.ticker, item.cotizacion.precio), ("BTC/USDT", D("60000")))

    def test_ficha_de_un_activo_inexistente_o_deshabilitado(self):
        for id_activo in (99, 5):
            with self.subTest(id_activo=id_activo):
                with self.assertRaises(ErrorOperacionInvalida):
                    self.servicio.obtener_activo(id_activo)


if __name__ == "__main__":
    unittest.main()
