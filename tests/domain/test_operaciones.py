"""Pruebas de las reglas puras de operar."""
import unittest
from datetime import datetime, timezone
from decimal import Decimal as D

from simultradia.domain.entities.posicion_entity import Posicion
from simultradia.domain.enums import LadoOrden, TipoOrden
from simultradia.domain.reglas.operaciones import (
    aplicar_compra, aplicar_venta, calcular_cantidad_por_riesgo, calcular_compra, cantidad_maxima_compra,
    estimar_orden, limite_alcanzado, precio_de_ejecucion, proteccion_alcanzada, redondear_nivel, riesgo_de_orden,
    riesgo_por_unidad, valorar_posicion)

AHORA = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)


class PruebasPrecioDeEjecucion(unittest.TestCase):
    def test_sin_deslizamiento_es_el_precio_exacto(self):
        self.assertEqual(precio_de_ejecucion(D("100"), LadoOrden.COMPRA, D("0")), D("100"))

    def test_la_compra_paga_mas_y_la_venta_recibe_menos(self):
        self.assertEqual(precio_de_ejecucion(D("100"), LadoOrden.COMPRA, D("1")), D("101"))
        self.assertEqual(precio_de_ejecucion(D("100"), LadoOrden.VENTA, D("1")), D("99"))


class PruebasCompra(unittest.TestCase):
    def test_monto_y_comision(self):
        self.assertEqual(calcular_compra(D("2"), D("100"), D("0.1")), (D("200"), D("0.2")))

    def test_el_precio_promedio_es_ponderado_y_las_comisiones_se_acumulan(self):
        vacia = Posicion(1, 1, D(0), D(0))
        p = aplicar_compra(vacia, D("1"), D("100"), D("0.1"))
        p = aplicar_compra(p, D("3"), D("200"), D("0.6"))
        self.assertEqual((p.cantidad, p.precio_promedio_entrada, p.comisiones_pagadas),
                         (D("4"), D("175"), D("0.7")))

    def test_la_cantidad_maxima_sin_comision(self):
        self.assertEqual(cantidad_maxima_compra(D("1000"), D("100"), D("0")), D("10"))

    def test_la_cantidad_maxima_nunca_se_pasa_del_saldo(self):
        for saldo, precio, pct in (("1000", "100", "1"), ("10000", "67123.45", "0.1"), ("10.5", "0.0000123", "0.1"),
                                   ("9999.9999", "3.3333", "0.25")):
            with self.subTest(saldo=saldo, precio=precio):
                q = cantidad_maxima_compra(D(saldo), D(precio), D(pct))
                monto, comision = calcular_compra(q, D(precio), D(pct))
                self.assertLessEqual(monto + comision, D(saldo))
                self.assertGreater(D(saldo) - monto - comision, D("-0.0001"))
                self.assertLess(D(saldo) - monto - comision, D("1"))     # aprovecha casi todo el saldo

    def test_sin_saldo_no_se_puede_comprar_nada(self):
        self.assertEqual(cantidad_maxima_compra(D("0"), D("100"), D("0.1")), D("0"))


class PruebasVenta(unittest.TestCase):
    def _posicion(self):
        return Posicion(1, 1, D("4"), D("175"), comisiones_pagadas=D("0.8"), abierta_en=AHORA, id_posicion=9)

    def test_venta_parcial(self):
        r = aplicar_venta(self._posicion(), D("1"), D("200"), D("0.1"), AHORA)
        self.assertEqual((r.ingreso_neto, r.comision), (D("199.8"), D("0.2")))
        # comisión de entrada proporcional: 0,8 x 1/4 = 0,2; ganancia = 25 - 0,2 - 0,2
        self.assertEqual((r.operacion.comisiones, r.operacion.ganancia_realizada), (D("0.4"), D("24.6")))
        self.assertEqual((r.posicion.cantidad, r.posicion.comisiones_pagadas), (D("3"), D("0.6")))
        self.assertEqual(r.posicion.precio_promedio_entrada, D("175"))

    def test_vender_todo_cierra_la_posicion_y_puede_dar_perdida(self):
        r = aplicar_venta(self._posicion(), D("4"), D("150"), D("0.1"), AHORA)
        self.assertIsNone(r.posicion)
        # (150-175) x 4 = -100; comisiones: 0,8 + 0,6 = 1,4
        self.assertEqual((r.operacion.comisiones, r.operacion.ganancia_realizada), (D("1.4"), D("-101.4")))
        self.assertEqual(r.operacion.abierta_en, AHORA)

    def test_no_modifica_la_posicion_original(self):
        p = self._posicion()
        aplicar_venta(p, D("1"), D("200"), D("0.1"), AHORA)
        self.assertEqual(p.cantidad, D("4"))


class PruebasEstimacion(unittest.TestCase):
    def test_estimar_una_compra(self):
        e = estimar_orden(LadoOrden.COMPRA, D("10"), D("100"), D("10000"), None, D("0.1"), D("0"), AHORA)
        self.assertEqual((e.precio, e.monto, e.comision, e.total, e.saldo_despues, e.ganancia),
                         (D("100"), D("1000"), D("1"), D("1001"), D("8999"), None))

    def test_estimar_una_venta_incluye_la_ganancia(self):
        p = Posicion(1, 1, D("10"), D("90"), comisiones_pagadas=D("0.9"), abierta_en=AHORA)
        e = estimar_orden(LadoOrden.VENTA, D("10"), D("100"), D("500"), p, D("0.1"), D("0"), AHORA)
        self.assertEqual((e.monto, e.comision, e.total, e.saldo_despues), (D("1000"), D("1"), D("999"), D("1499")))
        self.assertEqual(e.ganancia, D("98.1"))       # 100 de diferencia - 0,9 - 1

    def test_el_deslizamiento_cambia_el_precio_estimado(self):
        e = estimar_orden(LadoOrden.COMPRA, D("1"), D("100"), D("1000"), None, D("0"), D("1"), AHORA)
        self.assertEqual(e.precio, D("101"))


class PruebasValoracion(unittest.TestCase):
    def test_ganancia_no_realizada(self):
        p = Posicion(1, 1, D("2"), D("100"))
        self.assertEqual(valorar_posicion(p, D("110")), (D("220"), D("20"), D("10")))
        self.assertEqual(valorar_posicion(p, D("90")), (D("180"), D("-20"), D("-10")))


class PruebasRiesgo(unittest.TestCase):
    def test_riesgo_por_unidad_suma_la_caida_y_las_comisiones(self):
        self.assertEqual(riesgo_por_unidad(D("100"), D("90"), D("0")), D("10"))
        self.assertEqual(riesgo_por_unidad(D("100"), D("90"), D("0.1")), D("10.19"))

    def test_riesgo_de_una_orden(self):
        self.assertEqual(riesgo_de_orden(D("10"), D("100"), D("90"), D("0.1")), D("101.9"))

    def test_cantidad_para_arriesgar_un_monto(self):
        self.assertEqual(calcular_cantidad_por_riesgo(D("100"), D("100"), D("90"), D("0")), D("10"))
        q = calcular_cantidad_por_riesgo(D("100"), D("100"), D("90"), D("0.1"))
        self.assertTrue(D("9.81") < q < D("9.82"))
        self.assertLessEqual(riesgo_de_orden(q, D("100"), D("90"), D("0.1")), D("100"))

    def test_sin_distancia_al_stop_no_hay_cantidad(self):
        self.assertEqual(calcular_cantidad_por_riesgo(D("100"), D("100"), D("100"), D("0")), D("0"))
        self.assertEqual(calcular_cantidad_por_riesgo(D("100"), D("100"), D("120"), D("0")), D("0"))

    def test_niveles_con_los_decimales_con_que_se_muestran_los_precios(self):
        self.assertEqual(redondear_nivel(D("1234.5678")), D("1234.57"))
        self.assertEqual(redondear_nivel(D("12.34567")), D("12.3457"))
        self.assertEqual(redondear_nivel(D("0.1234567")), D("0.123457"))


class PruebasDisparadores(unittest.TestCase):
    def test_el_limite_de_compra_espera_a_que_el_precio_baje(self):
        self.assertFalse(limite_alcanzado(LadoOrden.COMPRA, D("100"), D("101")))
        self.assertTrue(limite_alcanzado(LadoOrden.COMPRA, D("100"), D("100")))
        self.assertTrue(limite_alcanzado(LadoOrden.COMPRA, D("100"), D("95")))

    def test_el_limite_de_venta_espera_a_que_el_precio_suba(self):
        self.assertFalse(limite_alcanzado(LadoOrden.VENTA, D("100"), D("99")))
        self.assertTrue(limite_alcanzado(LadoOrden.VENTA, D("100"), D("100")))
        self.assertTrue(limite_alcanzado(LadoOrden.VENTA, D("100"), D("105")))

    def test_protecciones(self):
        self.assertEqual(proteccion_alcanzada(D("90"), D("120"), D("90")), TipoOrden.STOP_LOSS)
        self.assertEqual(proteccion_alcanzada(D("90"), D("120"), D("85")), TipoOrden.STOP_LOSS)
        self.assertEqual(proteccion_alcanzada(D("90"), D("120"), D("120")), TipoOrden.TAKE_PROFIT)
        self.assertIsNone(proteccion_alcanzada(D("90"), D("120"), D("100")))
        self.assertIsNone(proteccion_alcanzada(None, None, D("1")))
        self.assertIsNone(proteccion_alcanzada(None, D("120"), D("50")))
        self.assertEqual(proteccion_alcanzada(D("90"), None, D("50")), TipoOrden.STOP_LOSS)


if __name__ == "__main__":
    unittest.main()
