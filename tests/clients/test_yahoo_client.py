"""Pruebas de cómo se convierten los datos de yfinance (sin internet: se usan tablas armadas a mano)."""
import unittest
from datetime import datetime, timezone
from decimal import Decimal as D

try:
    import pandas as pd
except ImportError:      # pandas llega con yfinance; sin él no hay nada que probar
    pd = None

from simultradia.clients.yahoo_client import YahooCliente, cotizaciones_desde_descarga, velas_desde_historial
from simultradia.domain.enums import IntervaloVela as I, TipoActivo

AHORA = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)


def _tabla(cierres, altos=None, bajos=None, volumen=None, indice=None):
    n = len(cierres)
    return pd.DataFrame({
        "Open": cierres, "High": altos or cierres, "Low": bajos or cierres, "Close": cierres,
        "Volume": volumen or [0] * n,
    }, index=indice if indice is not None else pd.date_range("2026-10-21", periods=n, freq="D"))


@unittest.skipIf(pd is None, "pandas no está instalado")
class PruebasCotizaciones(unittest.TestCase):
    def test_varios_activos_en_una_descarga(self):
        descarga = pd.concat({
            "AAPL": _tabla([100.0, 110.0], altos=[101.0, 112.0], bajos=[99.0, 108.0], volumen=[1000, 2000]),
            "EURUSD=X": _tabla([1.10, 1.1055]),
        }, axis=1)
        resultado = cotizaciones_desde_descarga(descarga, ["AAPL", "EURUSD=X"], AHORA)
        aapl = resultado["AAPL"]
        self.assertEqual((aapl.precio, aapl.cierre_anterior, aapl.variacion_pct_dia), (D("110.0"), D("100.0"), D("10.0")))
        self.assertEqual((aapl.maximo_dia, aapl.minimo_dia), (D("112.0"), D("108.0")))
        self.assertEqual(aapl.volumen_dia, D("220000.0"))            # 2000 acciones x 110 = dólares
        self.assertEqual(aapl.actualizado_en, AHORA)
        self.assertEqual(resultado["EURUSD=X"].precio, D("1.1055"))
        self.assertEqual(resultado["EURUSD=X"].volumen_dia, D("0"))  # las divisas no informan volumen

    def test_un_activo_sin_datos_no_aparece(self):
        descarga = pd.concat({"AAPL": _tabla([100.0, 101.0]), "MALO": _tabla([float("nan")] * 2)}, axis=1)
        resultado = cotizaciones_desde_descarga(descarga, ["AAPL", "MALO", "NOESTA"], AHORA)
        self.assertEqual(list(resultado), ["AAPL"])

    def test_un_solo_dia_de_datos_no_tiene_variacion(self):
        descarga = pd.concat({"AAPL": _tabla([100.0])}, axis=1)
        cot = cotizaciones_desde_descarga(descarga, ["AAPL"], AHORA)["AAPL"]
        self.assertEqual((cot.precio, cot.cierre_anterior, cot.variacion_pct_dia), (D("100.0"), None, None))

    def test_descarga_de_un_solo_activo_sin_nivel_de_ticker(self):
        resultado = cotizaciones_desde_descarga(_tabla([10.0, 11.0]), ["SPY"], AHORA)
        self.assertEqual(resultado["SPY"].precio, D("11.0"))


@unittest.skipIf(pd is None, "pandas no está instalado")
class PruebasVelas(unittest.TestCase):
    def test_las_velas_diarias_se_fijan_a_la_medianoche_utc_de_su_fecha(self):
        indice = pd.DatetimeIndex(["2026-10-22", "2026-10-23"], tz="America/New_York")   # 00:00 hora de Nueva York
        velas = velas_desde_historial(_tabla([10.0, 11.0], indice=indice), I.D1)
        self.assertEqual([v.momento for v in velas],
                         [datetime(2026, 10, 22, tzinfo=timezone.utc), datetime(2026, 10, 23, tzinfo=timezone.utc)])

    def test_las_velas_de_horas_se_pasan_a_utc(self):
        indice = pd.DatetimeIndex(["2026-10-23 09:30", "2026-10-23 10:30"], tz="America/New_York")
        velas = velas_desde_historial(_tabla([10.0, 11.0], indice=indice), I.H1)
        self.assertEqual(velas[0].momento, datetime(2026, 10, 23, 13, 30, tzinfo=timezone.utc))

    def test_se_saltan_las_filas_incompletas_y_se_corrigen_los_extremos(self):
        # La 3.ª fila viene con datos contradictorios (máximo 11,5 y mínimo 12,5, con apertura y cierre 12):
        # se ensanchan para que el máximo sea el mayor y el mínimo el menor, como exige la base.
        tabla = _tabla([10.0, float("nan"), 12.0], altos=[10.5, 11.0, 11.5], bajos=[9.0, 9.0, 12.5], volumen=[5, 5, 5])
        velas = velas_desde_historial(tabla, I.D1)
        self.assertEqual(len(velas), 2)                               # la fila con NaN se descartó
        self.assertEqual((velas[1].maximo, velas[1].minimo), (D("12.5"), D("11.5")))
        for v in velas:
            self.assertGreaterEqual(v.maximo, max(v.apertura, v.cierre, v.minimo))
            self.assertLessEqual(v.minimo, min(v.apertura, v.cierre))

    def test_sin_repetidas_y_en_orden(self):
        indice = pd.DatetimeIndex(["2026-10-23", "2026-10-22", "2026-10-23"])
        velas = velas_desde_historial(_tabla([10.0, 9.0, 11.0], indice=indice), I.D1)
        self.assertEqual([v.cierre for v in velas], [D("9.0"), D("11.0")])


class PruebasDeclaracion(unittest.TestCase):
    def test_declara_lo_que_ofrece(self):
        self.assertEqual(YahooCliente.NOMBRE, "Yahoo Finance")
        self.assertNotIn(TipoActivo.CRIPTO, YahooCliente.TIPOS)
        for ticker in ("AAPL", "EURUSD=X", "^GSPC", "BRK-B"):
            self.assertTrue(YahooCliente.PATRON_TICKER.match(ticker), ticker)
        self.assertIsNone(YahooCliente.PATRON_TICKER.match("BTC/USDT"))
        self.assertGreater(YahooCliente.segundos_entre_cotizaciones, 2)    # Yahoo exige ir más despacio que Binance


if __name__ == "__main__":
    unittest.main()
