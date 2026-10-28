"""Pruebas de SMA y EMA."""
import unittest

from simultradia.analisis.indicadores import bollinger, ema, macd, rsi, sma


class PruebasIndicadores(unittest.TestCase):
    def test_sma_promedia_los_ultimos_n_y_deja_none_al_inicio(self):
        self.assertEqual(sma([1, 2, 3, 4, 5], 3), [None, None, 2.0, 3.0, 4.0])

    def test_sma_con_menos_datos_que_el_periodo(self):
        self.assertEqual(sma([1, 2], 3), [None, None])

    def test_ema_arranca_con_la_sma_y_pesa_lo_reciente(self):
        resultado = ema([1, 2, 3, 4, 5], 3)
        self.assertEqual(resultado[:2], [None, None])
        self.assertAlmostEqual(resultado[2], 2.0)
        self.assertAlmostEqual(resultado[3], 3.0)    # 4*0.5 + 2*0.5
        self.assertAlmostEqual(resultado[4], 4.0)

    def test_ema_con_datos_insuficientes(self):
        self.assertEqual(ema([1, 2], 5), [None, None])

    def test_el_largo_siempre_coincide_con_la_entrada(self):
        datos = [float(i) for i in range(40)]
        self.assertEqual((len(sma(datos, 20)), len(ema(datos, 50))), (40, 40))


    # ------------------------------------------------------------ Bollinger
    def test_bollinger_en_una_serie_constante_las_bandas_coinciden_con_la_media(self):
        media, superior, inferior = bollinger([5.0] * 10, 5, 2.0)
        self.assertEqual(media[4:], [5.0] * 6)
        self.assertEqual((superior[4], inferior[4]), (5.0, 5.0))
        self.assertEqual((media[3], superior[3], inferior[3]), (None, None, None))

    def test_bollinger_las_bandas_son_simetricas_y_miden_la_desviacion(self):
        media, superior, inferior = bollinger([1.0, 3.0], 2, 2.0)
        self.assertEqual(media[1], 2.0)
        self.assertAlmostEqual(superior[1], 4.0)     # desviación = 1, banda = media + 2 * 1
        self.assertAlmostEqual(inferior[1], 0.0)

    # ------------------------------------------------------------------ RSI
    def test_rsi_de_una_serie_que_solo_sube_es_100_y_de_una_que_solo_baja_es_0(self):
        self.assertEqual(rsi([float(i) for i in range(1, 20)], 14)[-1], 100.0)
        self.assertEqual(rsi([float(i) for i in range(20, 1, -1)], 14)[-1], 0.0)

    def test_rsi_arranca_despues_del_periodo_y_de_una_serie_plana_es_50(self):
        resultado = rsi([float(i % 3) for i in range(30)], 14)
        self.assertEqual(resultado[:14], [None] * 14)
        self.assertIsNotNone(resultado[14])
        self.assertEqual(rsi([7.0] * 20, 14)[-1], 50.0)

    def test_rsi_siempre_esta_entre_0_y_100(self):
        datos = [100 + (7 * i) % 13 - (3 * i) % 5 for i in range(80)]
        valores = [v for v in rsi(datos, 14) if v is not None]
        self.assertTrue(valores and all(0.0 <= v <= 100.0 for v in valores))

    def test_rsi_con_pocos_datos(self):
        self.assertEqual(rsi([1.0, 2.0, 3.0], 14), [None, None, None])

    # ----------------------------------------------------------------- MACD
    def test_macd_es_positivo_en_una_tendencia_alcista_y_negativo_en_una_bajista(self):
        linea, senal, histograma = macd([float(i) for i in range(1, 80)])
        self.assertGreater(linea[-1], 0)
        linea, _s, _h = macd([float(i) for i in range(80, 1, -1)])
        self.assertLess(linea[-1], 0)

    def test_macd_largo_y_arranque_de_cada_serie(self):
        datos = [float(i) for i in range(60)]
        linea, senal, histograma = macd(datos, 12, 26, 9)
        self.assertEqual((len(linea), len(senal), len(histograma)), (60, 60, 60))
        self.assertEqual(linea.index(next(v for v in linea if v is not None)), 25)   # 26 datos para la lenta
        self.assertEqual(senal.index(next(v for v in senal if v is not None)), 33)   # +9 para la señal
        self.assertAlmostEqual(histograma[-1], linea[-1] - senal[-1])


if __name__ == "__main__":
    unittest.main()
