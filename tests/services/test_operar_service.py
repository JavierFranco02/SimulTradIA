"""Pruebas del servicio de Operar: órdenes a mercado y límite, stop-loss / take-profit, worker, permisos."""
import unittest
from datetime import datetime, timezone
from decimal import Decimal as D

from simultradia.core.exceptions import DatosInvalidos, ErrorOperacionInvalida, ErrorPermisos
from simultradia.domain.entities.activo_entity import Activo
from simultradia.domain.entities.cotizacion_entity import Cotizacion
from simultradia.domain.entities.cuenta_simulada_entity import CuentaSimulada
from simultradia.domain.entities.posicion_entity import Posicion
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.domain.enums import EstadoOrden, LadoOrden, RolUsuario, TipoOrden
from simultradia.services.operar_service import OperarService, SolicitudOrden
from tests.fakes import DatabaseFalsa, RepoActivoFalso, RepoPrecioFalso

AHORA = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
ANA = Usuario("Ana", "a@x.com", "h", id_usuario=2)
OTRA = Usuario("Otra", "o@x.com", "h", id_usuario=5)
ADMIN = Usuario("Jefe", "j@x.com", "h", rol=RolUsuario.ADMIN, id_usuario=1)
COMPRA, VENTA = LadoOrden.COMPRA, LadoOrden.VENTA
MERCADO, LIMITE = TipoOrden.MERCADO, TipoOrden.LIMITE


def _s(lado, cantidad, tipo=MERCADO, limite="", sl="", tp=""):
    return SolicitudOrden(lado, tipo, cantidad, limite, sl, tp)


class CuentaRepoFalso:
    def __init__(self, cuenta): self.cuenta = cuenta

    def buscar_de_usuario(self, conn, id_usuario, bloquear=False):
        return self.cuenta if self.cuenta and self.cuenta.id_usuario == id_usuario else None

    def buscar_por_id(self, conn, id_cuenta, bloquear=False):
        return self.cuenta if self.cuenta and self.cuenta.id_cuenta == id_cuenta else None

    def actualizar_saldo(self, conn, id_cuenta, saldo):
        self.cuenta.saldo_disponible = saldo
        return True


class PosicionRepoFalso:
    def __init__(self): self.posiciones, self.cerradas, self._id = {}, [], 1

    def buscar(self, conn, id_cuenta, id_activo): return self.posiciones.get((id_cuenta, id_activo))

    def listar(self, conn, id_cuenta): return [p for p in self.posiciones.values() if p.id_cuenta == id_cuenta]

    def listar_protegidas(self, conn):
        return [p for p in self.posiciones.values() if p.stop_loss is not None or p.take_profit is not None]

    def insertar(self, conn, p):
        p.id_posicion, self._id = self._id, self._id + 1
        self.posiciones[(p.id_cuenta, p.id_activo)] = p
        return p

    def actualizar(self, conn, p): self.posiciones[(p.id_cuenta, p.id_activo)] = p

    def borrar(self, conn, id_posicion):
        for clave, p in list(self.posiciones.items()):
            if p.id_posicion == id_posicion:
                del self.posiciones[clave]

    def insertar_operacion_cerrada(self, conn, o): self.cerradas.append(o); return o


class OrdenRepoFalso:
    def __init__(self): self.ordenes, self.ejecuciones = [], []

    def insertar_orden(self, conn, o):
        o.id_orden = len(self.ordenes) + 1
        self.ordenes.append(o)
        return o

    def buscar(self, conn, id_orden, bloquear=False):
        return next((o for o in self.ordenes if o.id_orden == id_orden), None)

    def insertar_ejecucion(self, conn, e):
        e.id_ejecucion = len(self.ejecuciones) + 1
        self.ejecuciones.append(e)
        return e

    def listar_ordenes(self, conn, id_cuenta, limite):
        return [o for o in reversed(self.ordenes) if o.estado != EstadoOrden.PENDIENTE][:limite]

    def listar_pendientes(self, conn, id_cuenta):
        return [o for o in self.ordenes if o.id_cuenta == id_cuenta and o.estado == EstadoOrden.PENDIENTE]

    def listar_pendientes_todas(self, conn):
        return [o for o in self.ordenes if o.estado == EstadoOrden.PENDIENTE]

    def marcar_ejecutada(self, conn, id_orden, precio, comision, ahora):
        o = self.buscar(conn, id_orden)
        o.estado, o.precio_promedio, o.comision_total, o.ejecutada_en = EstadoOrden.EJECUTADA, precio, comision, ahora

    def marcar_rechazada(self, conn, id_orden, motivo):
        o = self.buscar(conn, id_orden)
        o.estado, o.motivo_rechazo = EstadoOrden.RECHAZADA, motivo

    def cancelar(self, conn, id_orden, ahora):
        o = self.buscar(conn, id_orden)
        if o is None or o.estado != EstadoOrden.PENDIENTE:
            return False
        o.estado, o.cancelada_en = EstadoOrden.CANCELADA, ahora
        return True


class _Base(unittest.TestCase):
    def setUp(self):
        self.precios = RepoPrecioFalso()
        self.precios.cotizaciones[1] = Cotizacion(precio=D("100"), id_activo=1)
        self.precios.cotizaciones[3] = Cotizacion(precio=D("150"), id_activo=3)
        self.repo_activos = RepoActivoFalso([
            Activo("BTC/USDT", "Bitcoin", id_activo=1),
            Activo("NOPRECIO", "Sin precio", id_activo=2),
            Activo("USDJPY=X", "Dólar/Yen", moneda="JPY", id_activo=3),
            Activo("OLD/USDT", "Viejo", activo=False, id_activo=4)], self.precios)
        self.cuenta = CuentaSimulada(id_usuario=2, nombre="Cuenta principal", capital_inicial=D("10000"),
                                     saldo_disponible=D("10000"), id_cuenta=1, comision_pct=D("0.1"))
        self.cuentas, self.posiciones, self.ordenes = CuentaRepoFalso(self.cuenta), PosicionRepoFalso(), OrdenRepoFalso()
        self.servicio = OperarService(DatabaseFalsa(), self.cuentas, self.posiciones, self.ordenes,
                                      self.repo_activos, reloj=lambda: AHORA)

    def _resumen(self, id_activo=1):
        return self.servicio.obtener_resumen(ANA, id_activo)

    def _precio(self, valor, id_activo=1):
        self.precios.cotizaciones[id_activo] = Cotizacion(precio=D(valor), id_activo=id_activo)


class PruebasMercado(_Base):
    # ----------------------------------------------------------------- compra
    def test_comprar_descuenta_monto_y_comision_y_deja_constancia(self):
        e = self.servicio.comprar(ANA, 1, "10")
        self.assertEqual(self.cuenta.saldo_disponible, D("8999"))      # 10000 - 1000 - 1 de comisión
        p = self.posiciones.buscar(None, 1, 1)
        self.assertEqual((p.cantidad, p.precio_promedio_entrada, p.comisiones_pagadas), (D("10"), D("100"), D("1")))
        self.assertEqual((e.lado, e.cantidad, e.precio, e.comision, e.ticker),
                         (COMPRA, D("10"), D("100"), D("1"), "BTC/USDT"))
        self.assertEqual((len(self.ordenes.ordenes), self.ordenes.ordenes[0].estado), (1, EstadoOrden.EJECUTADA))
        self.assertEqual(self.ordenes.ejecuciones[0].id_orden, self.ordenes.ordenes[0].id_orden)

    def test_comprar_dos_veces_promedia_el_precio(self):
        self.servicio.comprar(ANA, 1, "10")
        self._precio("200")
        self.servicio.comprar(ANA, 1, "10")
        p = self.posiciones.buscar(None, 1, 1)
        self.assertEqual((p.cantidad, p.precio_promedio_entrada), (D("20"), D("150")))
        self.assertEqual(len(self.posiciones.posiciones), 1)

    def test_acepta_coma_decimal_y_espacios(self):
        self.assertEqual(self.servicio.comprar(ANA, 1, " 0,5 ").cantidad, D("0.5"))
        self.assertEqual(self.servicio.comprar(ANA, 1, "1\u00a0,5").cantidad, D("1.5"))

    def test_saldo_insuficiente_no_cambia_nada(self):
        with self.assertRaises(ErrorOperacionInvalida):
            self.servicio.comprar(ANA, 1, "100")                        # 10000 + comisión > saldo
        self.assertEqual(self.cuenta.saldo_disponible, D("10000"))
        self.assertEqual((self.posiciones.posiciones, self.ordenes.ordenes), ({}, []))

    def test_el_deslizamiento_empeora_el_precio(self):
        self.cuenta.deslizamiento_pct = D("1")
        self.assertEqual(self.servicio.comprar(ANA, 1, "1").precio, D("101"))
        self.assertEqual(self.servicio.vender(ANA, 1, "1").precio, D("99"))

    # ------------------------------------------------------------------ venta
    def test_vender_parte_deja_el_resto_y_registra_la_operacion_cerrada(self):
        self.servicio.comprar(ANA, 1, "10")
        self.servicio.vender(ANA, 1, "4")
        self.assertEqual(self.cuenta.saldo_disponible, D("9398.6"))     # 8999 + 400 - 0,4
        p = self.posiciones.buscar(None, 1, 1)
        self.assertEqual((p.cantidad, p.comisiones_pagadas), (D("6"), D("0.6")))
        [op] = self.posiciones.cerradas
        self.assertEqual((op.cantidad, op.comisiones, op.ganancia_realizada), (D("4"), D("0.8"), D("-0.8")))

    def test_vender_todo_borra_la_posicion(self):
        self.servicio.comprar(ANA, 1, "10")
        self.servicio.vender(ANA, 1, "10")
        self.assertEqual(self.posiciones.posiciones, {})
        self.assertEqual(self.cuenta.saldo_disponible, D("9998"))       # solo se pagó 1 + 1 de comisión

    def test_no_se_puede_vender_lo_que_no_se_tiene(self):
        with self.assertRaises(ErrorOperacionInvalida):
            self.servicio.vender(ANA, 1, "1")
        self.servicio.comprar(ANA, 1, "2")
        with self.assertRaises(ErrorOperacionInvalida):
            self.servicio.vender(ANA, 1, "3")
        self.assertEqual(len(self.ordenes.ordenes), 1)

    def test_vender_todo_cierra_la_posicion_sin_indicar_cantidad(self):
        self.servicio.comprar(ANA, 1, "10")
        e = self.servicio.vender_todo(ANA, 1)
        self.assertEqual((e.lado, e.cantidad), (VENTA, D("10")))
        self.assertEqual((self.posiciones.posiciones, self.cuenta.saldo_disponible), ({}, D("9998")))

    def test_vender_todo_sin_posicion(self):
        with self.assertRaises(ErrorOperacionInvalida):
            self.servicio.vender_todo(ANA, 1)

    def test_cerrar_todas_sigue_aunque_una_falle(self):
        self.servicio.comprar(ANA, 1, "10")
        self.posiciones.insertar(None, Posicion(1, 2, D("1"), D("5")))      # activo sin precio: no se puede vender
        r = self.servicio.cerrar_todas(ANA)
        self.assertEqual(r.cerradas, 1)
        self.assertEqual(len(r.fallidas), 1)
        self.assertIn("NOPRECIO", r.fallidas[0])
        self.assertEqual(list(self.posiciones.posiciones), [(1, 2)])

    # ---------------------------------------------------------- validaciones
    def test_cantidades_invalidas(self):
        for texto in ("", "abc", "0", "-1", "nan", "inf", "1e100", "0,00000000001"):
            with self.subTest(texto=texto):
                with self.assertRaises(DatosInvalidos) as c:
                    self.servicio.comprar(ANA, 1, texto)
                self.assertEqual(list(c.exception.errores), ["cantidad"])
        self.assertEqual(self.ordenes.ordenes, [])

    def test_activo_inexistente_deshabilitado_sin_precio_o_en_otra_moneda(self):
        for id_activo in (99, 4, 2, 3):
            with self.subTest(id_activo=id_activo):
                with self.assertRaises(ErrorOperacionInvalida):
                    self.servicio.comprar(ANA, id_activo, "1")
        self.assertEqual(self.cuenta.saldo_disponible, D("10000"))

    def test_sin_cuenta_simulada(self):
        self.cuentas.cuenta = None
        with self.assertRaises(ErrorOperacionInvalida):
            self.servicio.comprar(ANA, 1, "1")

    # --------------------------------------------------------------- permisos
    def test_el_administrador_y_los_anonimos_no_operan(self):
        for actor in (ADMIN, None):
            for llamada in (lambda a: self.servicio.comprar(a, 1, "1"), lambda a: self.servicio.vender(a, 1, "1"),
                            lambda a: self.servicio.enviar(a, 1, _s(COMPRA, "1", LIMITE, "90")),
                            lambda a: self.servicio.vender_todo(a, 1), lambda a: self.servicio.cerrar_todas(a),
                            lambda a: self.servicio.cancelar_orden(a, 1),
                            lambda a: self.servicio.editar_proteccion(a, 1, "90", ""),
                            lambda a: self.servicio.obtener_estado(a, 1), lambda a: self.servicio.obtener_resumen(a, 1),
                            lambda a: self.servicio.listar_historial(a), lambda a: self.servicio.listar_posiciones(a)):
                with self.assertRaises(ErrorPermisos):
                    llamada(actor)
        self.assertEqual(self.ordenes.ordenes, [])

    # ------------------------------------------------------- estimar y atajos
    def test_estimar_una_compra(self):
        e = self.servicio.estimar(self._resumen(), _s(COMPRA, "10"))
        self.assertEqual((e.precio, e.monto, e.comision, e.total, e.saldo_despues, e.ganancia),
                         (D("100"), D("1000"), D("1"), D("1001"), D("8999"), None))
        self.assertEqual(self.ordenes.ordenes, [])                      # estimar no ejecuta nada

    def test_estimar_una_venta(self):
        self.servicio.comprar(ANA, 1, "10")
        e = self.servicio.estimar(self._resumen(), _s(VENTA, "4"))
        self.assertEqual((e.monto, e.comision, e.total, e.saldo_despues, e.ganancia),
                         (D("400"), D("0.4"), D("399.6"), D("9398.6"), D("-0.8")))

    def test_estimar_da_el_mismo_error_que_enviar(self):
        resumen = self.servicio.obtener_resumen(ANA, 1)
        for solicitud, error in ((_s(COMPRA, "100"), ErrorOperacionInvalida), (_s(VENTA, "1"), ErrorOperacionInvalida),
                                 (_s(COMPRA, ""), DatosInvalidos), (_s(COMPRA, "abc"), DatosInvalidos)):
            with self.subTest(solicitud=solicitud):
                with self.assertRaises(error):
                    self.servicio.estimar(resumen, solicitud)

    def test_cantidad_para_al_comprar_es_un_porcentaje_de_lo_que_alcanza(self):
        resumen = self._resumen()
        todo = self.servicio.cantidad_para(resumen, _s(COMPRA, ""), 100)
        e = self.servicio.estimar(resumen, _s(COMPRA, str(todo)))
        self.assertTrue(D("0") <= e.saldo_despues < D("1"))              # aprovecha casi todo el saldo
        mitad = self.servicio.cantidad_para(resumen, _s(COMPRA, ""), 50)
        self.assertTrue(D("49.9") < mitad < D("50"))

    def test_cantidad_para_en_una_compra_limite_usa_el_precio_limite(self):
        resumen = self._resumen()
        todo = self.servicio.cantidad_para(resumen, _s(COMPRA, "", LIMITE, "50"), 100)
        self.assertTrue(D("199") < todo < D("200"))                      # 10000 / 50, menos la comisión

    def test_cantidad_para_al_vender_es_un_porcentaje_de_la_posicion(self):
        self.servicio.comprar(ANA, 1, "10")
        resumen = self._resumen()
        self.assertEqual(self.servicio.cantidad_para(resumen, _s(VENTA, ""), 25), D("2.5"))
        self.assertEqual(self.servicio.cantidad_para(resumen, _s(VENTA, ""), 100), D("10"))

    def test_cantidad_para_sin_nada_que_usar(self):
        with self.assertRaises(ErrorOperacionInvalida):
            self.servicio.cantidad_para(self._resumen(), _s(VENTA, ""), 50)      # no tiene el activo
        self.cuenta.saldo_disponible = D("0")
        with self.assertRaises(ErrorOperacionInvalida):
            self.servicio.cantidad_para(self._resumen(), _s(COMPRA, ""), 50)     # sin saldo

    # -------------------------------------------------------------- consultas
    def test_resumen_con_y_sin_posicion(self):
        r = self._resumen()
        self.assertEqual((r.saldo_disponible, r.moneda, r.posicion, r.item.activo.ticker),
                         (D("10000"), "USD", None, "BTC/USDT"))
        self.servicio.comprar(ANA, 1, "1")
        self.assertEqual(self._resumen().posicion.cantidad, D("1"))

    def test_el_resumen_trae_la_ganancia_no_realizada_de_la_posicion(self):
        self.assertEqual((self._resumen().ganancia, self._resumen().ganancia_pct), (None, None))
        self.servicio.comprar(ANA, 1, "10")
        self._precio("110")
        r = self._resumen()
        self.assertEqual((r.ganancia, r.ganancia_pct), (D("100"), D("10")))

    def test_el_resumen_de_un_activo_sin_precio_no_falla(self):
        self.assertIsNone(self._resumen(2).item.cotizacion)

    def test_posiciones_con_ganancia_no_realizada_al_precio_de_ahora(self):
        self.servicio.comprar(ANA, 1, "10")
        self._precio("110")
        [v] = self.servicio.listar_posiciones(ANA)
        self.assertEqual((v.ticker, v.precio_actual, v.valor, v.ganancia, v.ganancia_pct),
                         ("BTC/USDT", D("110"), D("1100"), D("100"), D("10")))

    def test_una_posicion_sin_precio_se_lista_sin_ganancia(self):
        self.posiciones.insertar(None, Posicion(1, 2, D("1"), D("5")))
        [v] = self.servicio.listar_posiciones(ANA)
        self.assertEqual((v.ticker, v.valor, v.ganancia, v.ganancia_pct), ("NOPRECIO", None, None, None))

    def test_historial_de_ordenes_de_lo_mas_nuevo_a_lo_mas_viejo(self):
        self.servicio.comprar(ANA, 1, "1")
        self.servicio.vender(ANA, 1, "1")
        self.assertEqual([o.lado for o in self.servicio.listar_historial(ANA)], [VENTA, COMPRA])

    def test_obtener_estado_trae_todo_junto(self):
        self.servicio.comprar(ANA, 1, "10")
        self.servicio.enviar(ANA, 1, _s(COMPRA, "1", LIMITE, "90"))
        estado = self.servicio.obtener_estado(ANA, 1)
        self.assertEqual((estado.resumen.posicion.cantidad, len(estado.posiciones), len(estado.pendientes),
                          len(estado.historial)), (D("10"), 1, 1, 1))

    def test_obtener_estado_sin_activo_elegido_o_con_uno_que_ya_no_existe(self):
        self.assertIsNone(self.servicio.obtener_estado(ANA, None).resumen)
        self.assertIsNone(self.servicio.obtener_estado(ANA, 4).resumen)         # deshabilitado: el panel no se rompe


class PruebasLimite(_Base):
    def _pendiente(self, lado=COMPRA, cantidad="10", limite="90", sl="", tp=""):
        return self.servicio.enviar(ANA, 1, _s(lado, cantidad, LIMITE, limite, sl, tp)).pendiente

    def test_una_orden_limite_queda_pendiente_sin_mover_dinero(self):
        r = self.servicio.enviar(ANA, 1, _s(COMPRA, "10", LIMITE, "90"))
        self.assertIsNone(r.ejecucion)
        self.assertEqual((r.pendiente.estado, r.pendiente.tipo, r.pendiente.precio_limite, r.pendiente.ticker),
                         (EstadoOrden.PENDIENTE, LIMITE, D("90"), "BTC/USDT"))
        self.assertEqual((self.cuenta.saldo_disponible, self.posiciones.posiciones, self.ordenes.ejecuciones),
                         (D("10000"), {}, []))

    def test_validaciones_del_limite(self):
        casos = (("compra por encima del precio", _s(COMPRA, "1", LIMITE, "100"), "precio_limite"),
                 ("venta por debajo del precio", _s(VENTA, "1", LIMITE, "100"), "precio_limite"),
                 ("sin precio límite", _s(COMPRA, "1", LIMITE, ""), "precio_limite"),
                 ("precio límite inválido", _s(COMPRA, "1", LIMITE, "abc"), "precio_limite"),
                 ("precio límite cero", _s(COMPRA, "1", LIMITE, "0"), "precio_limite"))
        self.servicio.comprar(ANA, 1, "5")
        for nombre, solicitud, campo in casos:
            with self.subTest(nombre):
                with self.assertRaises(DatosInvalidos) as c:
                    self.servicio.enviar(ANA, 1, solicitud)
                self.assertEqual(list(c.exception.errores), [campo])
        self.assertEqual(len(self.ordenes.ordenes), 1)                  # solo la compra a mercado

    def test_se_valida_el_saldo_al_enviar_aunque_no_se_reserve(self):
        with self.assertRaises(ErrorOperacionInvalida):
            self.servicio.enviar(ANA, 1, _s(COMPRA, "1000", LIMITE, "90"))
        self.assertEqual(self.ordenes.ordenes, [])

    def test_un_tipo_de_orden_no_disponible(self):
        with self.assertRaises(ErrorOperacionInvalida):
            self.servicio.enviar(ANA, 1, _s(COMPRA, "1", TipoOrden.STOP_LOSS))

    def test_estimar_una_compra_limite_usa_el_precio_limite(self):
        e = self.servicio.estimar(self._resumen(), _s(COMPRA, "10", LIMITE, "90"))
        self.assertEqual((e.precio, e.monto, e.comision), (D("90"), D("900"), D("0.9")))

    def test_cancelar_una_orden_pendiente(self):
        orden = self._pendiente()
        self.servicio.cancelar_orden(ANA, orden.id_orden)
        self.assertEqual((orden.estado, orden.cancelada_en), (EstadoOrden.CANCELADA, AHORA))
        self.assertEqual(self.servicio.obtener_estado(ANA, 1).pendientes, [])
        with self.assertRaises(ErrorOperacionInvalida):
            self.servicio.cancelar_orden(ANA, orden.id_orden)           # ya no está pendiente

    def test_no_se_puede_cancelar_la_orden_de_otro_o_una_que_no_existe(self):
        orden = self._pendiente()
        self.cuentas.cuenta.id_usuario = 5                               # la cuenta pasa a ser de OTRA
        for id_orden in (orden.id_orden, 99):
            with self.assertRaises(ErrorOperacionInvalida):
                self.servicio.cancelar_orden(ANA, id_orden)

    # ---------------------------------------------------------------- el worker
    def test_el_worker_ejecuta_la_compra_limite_cuando_el_precio_baja(self):
        orden = self._pendiente(limite="90")
        self.assertEqual(self.servicio.evaluar_pendientes().ejecutadas, 0)   # el precio sigue en 100
        self._precio("88")
        r = self.servicio.evaluar_pendientes()
        self.assertEqual((r.ejecutadas, r.rechazadas), (1, 0))
        self.assertEqual((orden.estado, orden.precio_promedio), (EstadoOrden.EJECUTADA, D("88")))   # al precio de ahora
        self.assertEqual(self.posiciones.buscar(None, 1, 1).cantidad, D("10"))
        self.assertEqual(self.cuenta.saldo_disponible, D("9119.12"))     # 10000 - 880 - 0,88
        self.assertEqual(self.ordenes.ejecuciones[0].id_orden, orden.id_orden)
        self.assertEqual(self.servicio.evaluar_pendientes().ejecutadas, 0)   # no se ejecuta dos veces

    def test_el_worker_ejecuta_la_venta_limite_cuando_el_precio_sube(self):
        self.servicio.comprar(ANA, 1, "10")
        orden = self._pendiente(lado=VENTA, cantidad="4", limite="120")
        self._precio("121")
        self.assertEqual(self.servicio.evaluar_pendientes().ejecutadas, 1)
        self.assertEqual((orden.estado, self.posiciones.buscar(None, 1, 1).cantidad), (EstadoOrden.EJECUTADA, D("6")))

    def test_la_orden_limite_no_aplica_deslizamiento(self):
        self.cuenta.deslizamiento_pct = D("1")
        self._pendiente(limite="90")
        self._precio("88")
        self.servicio.evaluar_pendientes()
        self.assertEqual(self.ordenes.ejecuciones[0].precio, D("88"))

    def test_si_al_ejecutarse_ya_no_hay_saldo_queda_rechazada_con_su_motivo(self):
        orden = self._pendiente(cantidad="100", limite="90")             # 9000 de 10000: alcanza al enviarla
        self.servicio.comprar(ANA, 1, "50")                              # el usuario gasta el saldo antes
        self._precio("89")
        r = self.servicio.evaluar_pendientes()
        self.assertEqual((r.ejecutadas, r.rechazadas), (0, 1))
        self.assertEqual(orden.estado, EstadoOrden.RECHAZADA)
        self.assertIn("Saldo insuficiente", orden.motivo_rechazo)
        self.assertIn(orden.id_orden, [o.id_orden for o in self.servicio.listar_historial(ANA)])   # sale en el historial

    def test_una_venta_limite_sin_posicion_queda_rechazada(self):
        self.servicio.comprar(ANA, 1, "5")
        orden = self._pendiente(lado=VENTA, cantidad="5", limite="120")
        self.servicio.vender_todo(ANA, 1)
        self._precio("125")
        self.assertEqual(self.servicio.evaluar_pendientes().rechazadas, 1)
        self.assertEqual(orden.estado, EstadoOrden.RECHAZADA)

    def test_una_orden_cancelada_no_se_ejecuta(self):
        orden = self._pendiente(limite="90")
        self.servicio.cancelar_orden(ANA, orden.id_orden)
        self._precio("80")
        self.assertEqual(self.servicio.evaluar_pendientes().ejecutadas, 0)
        self.assertEqual(self.posiciones.posiciones, {})


class PruebasProteccion(_Base):
    def test_comprar_con_stop_loss_y_take_profit_los_deja_en_la_posicion(self):
        self.servicio.enviar(ANA, 1, _s(COMPRA, "10", sl="90", tp="120"))
        p = self.posiciones.buscar(None, 1, 1)
        self.assertEqual((p.stop_loss, p.take_profit), (D("90"), D("120")))

    def test_los_niveles_se_validan_contra_el_precio_de_compra(self):
        for solicitud, campo in ((_s(COMPRA, "1", sl="100"), "stop_loss"), (_s(COMPRA, "1", sl="110"), "stop_loss"),
                                 (_s(COMPRA, "1", tp="100"), "take_profit"), (_s(COMPRA, "1", tp="95"), "take_profit"),
                                 (_s(COMPRA, "1", sl="abc"), "stop_loss")):
            with self.subTest(solicitud=solicitud):
                with self.assertRaises(DatosInvalidos) as c:
                    self.servicio.enviar(ANA, 1, solicitud)
                self.assertEqual(list(c.exception.errores), [campo])
        self.assertEqual(self.ordenes.ordenes, [])

    def test_al_vender_no_se_aceptan_niveles(self):
        self.servicio.comprar(ANA, 1, "5")
        with self.assertRaises(ErrorOperacionInvalida):
            self.servicio.enviar(ANA, 1, _s(VENTA, "1", sl="90"))

    def test_una_compra_sin_niveles_conserva_los_que_ya_tenia_la_posicion(self):
        self.servicio.enviar(ANA, 1, _s(COMPRA, "5", sl="90"))
        self.servicio.comprar(ANA, 1, "5")
        self.assertEqual(self.posiciones.buscar(None, 1, 1).stop_loss, D("90"))
        self.servicio.enviar(ANA, 1, _s(COMPRA, "5", sl="95"))
        self.assertEqual(self.posiciones.buscar(None, 1, 1).stop_loss, D("95"))

    def test_una_compra_limite_con_niveles_los_pone_al_ejecutarse(self):
        self.servicio.enviar(ANA, 1, _s(COMPRA, "10", LIMITE, "90", sl="80", tp="120"))
        self._precio("89")
        self.servicio.evaluar_pendientes()
        p = self.posiciones.buscar(None, 1, 1)
        self.assertEqual((p.stop_loss, p.take_profit), (D("80"), D("120")))

    def test_editar_poner_cambiar_y_quitar(self):
        self.servicio.comprar(ANA, 1, "10")
        self.servicio.editar_proteccion(ANA, 1, "90", "120,5")
        p = self.posiciones.buscar(None, 1, 1)
        self.assertEqual((p.stop_loss, p.take_profit), (D("90"), D("120.5")))
        self.servicio.editar_proteccion(ANA, 1, "", "130")
        p = self.posiciones.buscar(None, 1, 1)
        self.assertEqual((p.stop_loss, p.take_profit), (None, D("130")))
        self.servicio.editar_proteccion(ANA, 1, "", "")
        self.assertEqual(self.posiciones.buscar(None, 1, 1).take_profit, None)

    def test_editar_valida_contra_el_precio_actual(self):
        self.servicio.comprar(ANA, 1, "10")
        with self.assertRaises(DatosInvalidos) as c:
            self.servicio.editar_proteccion(ANA, 1, "100", "100")
        self.assertEqual(sorted(c.exception.errores), ["stop_loss", "take_profit"])
        with self.assertRaises(ErrorOperacionInvalida):
            self.servicio.editar_proteccion(ANA, 4, "90", "")            # activo deshabilitado
        self.assertIsNone(self.posiciones.buscar(None, 1, 1).stop_loss)

    def test_editar_sin_posicion(self):
        with self.assertRaises(ErrorOperacionInvalida):
            self.servicio.editar_proteccion(ANA, 1, "90", "")

    # ---------------------------------------------------------------- el worker
    def test_el_stop_loss_vende_toda_la_posicion(self):
        self.servicio.enviar(ANA, 1, _s(COMPRA, "10", sl="90", tp="120"))
        self.assertEqual(self.servicio.evaluar_pendientes().ejecutadas, 0)
        self._precio("89")
        self.assertEqual(self.servicio.evaluar_pendientes().ejecutadas, 1)
        self.assertEqual(self.posiciones.posiciones, {})
        [orden] = [o for o in self.ordenes.ordenes if o.lado == VENTA]
        self.assertEqual((orden.tipo, orden.estado, orden.precio_promedio),
                         (TipoOrden.STOP_LOSS, EstadoOrden.EJECUTADA, D("89")))
        [op] = self.posiciones.cerradas
        self.assertLess(op.ganancia_realizada, 0)

    def test_el_take_profit_vende_toda_la_posicion(self):
        self.servicio.enviar(ANA, 1, _s(COMPRA, "10", sl="90", tp="120"))
        self._precio("121")
        self.assertEqual(self.servicio.evaluar_pendientes().ejecutadas, 1)
        self.assertEqual(self.posiciones.posiciones, {})
        [orden] = [o for o in self.ordenes.ordenes if o.lado == VENTA]
        self.assertEqual(orden.tipo, TipoOrden.TAKE_PROFIT)
        [op] = self.posiciones.cerradas
        self.assertGreater(op.ganancia_realizada, 0)

    def test_el_stop_loss_si_aplica_deslizamiento_y_el_take_profit_no(self):
        self.cuenta.deslizamiento_pct = D("1")
        self.servicio.enviar(ANA, 1, _s(COMPRA, "10", sl="90", tp="120"))
        self._precio("89")
        self.servicio.evaluar_pendientes()
        self.assertEqual(self.ordenes.ejecuciones[-1].precio, D("88.11"))   # 89 menos el 1 %
        self._precio("100")
        self.servicio.enviar(ANA, 1, _s(COMPRA, "10", sl="90", tp="120"))
        self._precio("121")
        self.servicio.evaluar_pendientes()
        self.assertEqual(self.ordenes.ejecuciones[-1].precio, D("121"))

    def test_si_la_posicion_se_cerro_antes_no_pasa_nada(self):
        self.servicio.enviar(ANA, 1, _s(COMPRA, "10", sl="90"))
        self.servicio.vender_todo(ANA, 1)
        self._precio("80")
        self.assertEqual(self.servicio.evaluar_pendientes().ejecutadas, 0)

    def test_una_posicion_sin_niveles_no_se_toca(self):
        self.servicio.comprar(ANA, 1, "10")
        self._precio("1")
        self.assertEqual(self.servicio.evaluar_pendientes().ejecutadas, 0)
        self.assertEqual(self.posiciones.buscar(None, 1, 1).cantidad, D("10"))


if __name__ == "__main__":
    unittest.main()
