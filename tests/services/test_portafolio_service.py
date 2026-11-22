"""Pruebas del servicio de Portafolio: la foto del patrimonio, la curva, las métricas y los permisos."""
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

from simultradia.core.exceptions import ErrorOperacionInvalida, ErrorPermisos
from simultradia.domain.entities.activo_entity import Activo
from simultradia.domain.entities.cotizacion_entity import Cotizacion
from simultradia.domain.entities.cuenta_simulada_entity import CuentaSimulada
from simultradia.domain.entities.operacion_cerrada_entity import OperacionCerrada
from simultradia.domain.entities.posicion_entity import Posicion
from simultradia.domain.entities.snapshot_entity import SnapshotPortafolio
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.domain.enums import RolUsuario
from simultradia.services.portafolio_service import PortafolioService
from tests.fakes import DatabaseFalsa, RepoActivoFalso, RepoPrecioFalso

AHORA = datetime(2026, 11, 16, 9, 37, 25, tzinfo=timezone.utc)
CREADA = datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc)
ANA = Usuario("Ana", "a@x.com", "h", id_usuario=2)
ADMIN = Usuario("Jefe", "j@x.com", "h", rol=RolUsuario.ADMIN, id_usuario=1)


class CuentaRepoFalso:
    def __init__(self, *cuentas): self.cuentas = list(cuentas)
    def listar_operables(self, conn): return list(self.cuentas)

    def buscar_de_usuario(self, conn, id_usuario, bloquear=False):
        return next((c for c in self.cuentas if c.id_usuario == id_usuario), None)


class PosicionRepoFalso:
    def __init__(self, posiciones=(), cerradas=()):
        self.posiciones, self.cerradas = list(posiciones), list(cerradas)

    def listar(self, conn, id_cuenta): return [p for p in self.posiciones if p.id_cuenta == id_cuenta]
    def listar_operaciones_cerradas(self, conn, id_cuenta): return [o for o in self.cerradas if o.id_cuenta == id_cuenta]


class SnapshotRepoFalso:
    def __init__(self): self.filas, self.compactaciones = {}, []

    def guardar(self, conn, s): self.filas[(s.id_cuenta, s.momento)] = s

    def compactar(self, conn, antes_de):
        """Igual que el real: de lo anterior a `antes_de`, una sola foto por cuenta y hora (la última)."""
        self.compactaciones.append(antes_de)
        ultimas = {}
        for (cuenta, momento) in sorted(self.filas):
            if momento < antes_de:
                ultimas[(cuenta, momento.replace(minute=0))] = momento
        for (cuenta, momento) in list(self.filas):
            if momento < antes_de and ultimas[(cuenta, momento.replace(minute=0))] != momento:
                del self.filas[(cuenta, momento)]

    def listar(self, conn, id_cuenta):
        return sorted((s for (c, _m), s in self.filas.items() if c == id_cuenta), key=lambda s: s.momento)


def _cuenta(id_cuenta=1, id_usuario=2, saldo="6000", creada=CREADA):
    return CuentaSimulada(id_usuario=id_usuario, nombre="Cuenta principal", capital_inicial=D("10000"),
                          saldo_disponible=D(saldo), id_cuenta=id_cuenta, creada_en=creada)


def _cerrada(ganancia, comisiones="1"):
    return OperacionCerrada(1, 1, D("2"), D("100"), D("110"), D(comisiones), D(ganancia), CREADA, AHORA,
                            id_operacion_cerrada=1, ticker="BTC/USDT")


class _Base(unittest.TestCase):
    def setUp(self):
        self.precios = RepoPrecioFalso()
        self.precios.cotizaciones[1] = Cotizacion(precio=D("100"), id_activo=1)
        self.activos = RepoActivoFalso([Activo("BTC/USDT", "Bitcoin", id_activo=1),
                                        Activo("SINPRECIO", "Sin precio", id_activo=2)], self.precios)
        self.cuentas = CuentaRepoFalso(_cuenta())
        self.posiciones = PosicionRepoFalso([Posicion(1, 1, D("10"), D("90"), comisiones_pagadas=D("0.9"))])
        self.snapshots = SnapshotRepoFalso()
        self.ahora = AHORA
        self.servicio = PortafolioService(DatabaseFalsa(), self.cuentas, self.posiciones, self.activos,
                                          self.snapshots, reloj=lambda: self.ahora)


class PruebasGuardarSnapshots(_Base):
    def test_guarda_la_foto_del_minuto_en_curso_con_saldo_y_posiciones(self):
        self.assertEqual(self.servicio.guardar_snapshots(), 1)
        momento = datetime(2026, 11, 16, 9, 37, tzinfo=timezone.utc)
        s = self.snapshots.filas[(1, momento)]
        self.assertEqual((s.saldo_disponible, s.valor_posiciones, s.patrimonio_total),
                         (D("6000"), D("1000"), D("7000")))

    def test_repetirlo_en_el_mismo_minuto_actualiza_la_foto_en_vez_de_agregar_otra(self):
        self.servicio.guardar_snapshots()
        self.precios.cotizaciones[1] = Cotizacion(precio=D("120"), id_activo=1)
        self.servicio.guardar_snapshots()
        self.assertEqual(len(self.snapshots.filas), 1)
        self.assertEqual(list(self.snapshots.filas.values())[0].patrimonio_total, D("7200"))

    def test_en_otro_minuto_agrega_una_foto_nueva(self):
        self.servicio.guardar_snapshots()
        self.ahora = AHORA + timedelta(minutes=1)
        self.servicio.guardar_snapshots()
        self.assertEqual(len(self.snapshots.filas), 2)

    def test_una_posicion_sin_precio_se_valora_a_lo_que_costo(self):
        self.posiciones.posiciones.append(Posicion(1, 2, D("2"), D("5")))
        self.servicio.guardar_snapshots()
        self.assertEqual(list(self.snapshots.filas.values())[0].valor_posiciones, D("1010"))

    def test_guarda_una_foto_por_cuenta(self):
        self.cuentas.cuentas.append(_cuenta(id_cuenta=2, id_usuario=3, saldo="500"))
        self.assertEqual(self.servicio.guardar_snapshots(), 2)
        self.assertEqual(sorted(c for c, _m in self.snapshots.filas), [1, 2])

    def test_sin_cuentas_no_guarda_nada(self):
        self.cuentas.cuentas.clear()
        self.assertEqual(self.servicio.guardar_snapshots(), 0)
        self.assertEqual(self.snapshots.filas, {})

    def test_lo_de_mas_de_7_dias_se_compacta_a_una_foto_por_hora(self):
        vieja = datetime(2026, 11, 1, 5, 0, tzinfo=timezone.utc)                  # hace más de 7 días
        for minutos in (0, 20, 40, 59):
            self.snapshots.guardar(None, SnapshotPortafolio(1, vieja + timedelta(minutes=minutos), D(1), D(0), D(1)))
        reciente = AHORA - timedelta(days=1)
        for minutos in (0, 1, 2):
            self.snapshots.guardar(None, SnapshotPortafolio(1, reciente + timedelta(minutes=minutos), D(1), D(0), D(1)))
        self.servicio.guardar_snapshots()
        antiguas = [m for (_c, m) in self.snapshots.filas if m < AHORA - timedelta(days=7)]
        self.assertEqual(antiguas, [vieja + timedelta(minutes=59)])                # queda la última de esa hora
        self.assertEqual(len([m for (_c, m) in self.snapshots.filas if m >= reciente]), 4)    # lo reciente, intacto (3 + la de ahora)

    def test_compacta_una_sola_vez_por_hora(self):
        self.servicio.guardar_snapshots()
        self.ahora = AHORA + timedelta(minutes=5)
        self.servicio.guardar_snapshots()
        self.assertEqual(len(self.snapshots.compactaciones), 1)
        self.ahora = AHORA + timedelta(hours=1)
        self.servicio.guardar_snapshots()
        self.assertEqual(len(self.snapshots.compactaciones), 2)
        self.assertEqual(self.snapshots.compactaciones[0], datetime(2026, 11, 9, 9, 0, tzinfo=timezone.utc))


class PruebasObtenerPortafolio(_Base):
    def _foto(self, dias_antes, patrimonio):
        momento = AHORA.replace(minute=0, second=0) - timedelta(days=dias_antes)
        self.snapshots.guardar(None, SnapshotPortafolio(1, momento, D(patrimonio), D("0"), D(patrimonio)))

    def test_cifras_de_la_cuenta(self):
        r = self.servicio.obtener_portafolio(ANA)
        self.assertEqual((r.patrimonio, r.saldo_disponible, r.valor_posiciones, r.moneda),
                         (D("7000"), D("6000"), D("1000"), "USD"))
        self.assertEqual((r.rentabilidad_pct, r.exposicion_pct), (D("-30"), D("14.2857")))
        self.assertEqual(r.pnl_no_realizado, D("100"))            # (100 - 90) x 10

    def test_la_curva_arranca_con_el_capital_inicial_y_termina_en_este_minuto(self):
        self._foto(4, "10400")
        self._foto(1, "10097")
        r = self.servicio.obtener_portafolio(ANA)
        self.assertEqual(len(r.puntos), 4)                        # inicio + 2 fotos + la de este minuto
        self.assertEqual((r.puntos[0].momento, r.puntos[0].patrimonio_total), (CREADA, D("10000")))
        self.assertEqual((r.puntos[-1].momento, r.puntos[-1].patrimonio_total),
                         (datetime(2026, 11, 16, 9, 37, tzinfo=timezone.utc), D("7000")))
        self.assertEqual(len(r.caidas), len(r.puntos))

    def test_abrir_portafolio_guarda_la_foto_del_minuto_aunque_el_worker_este_apagado(self):
        self.assertEqual(self.snapshots.filas, {})
        self.servicio.obtener_portafolio(ANA)
        self.servicio.obtener_portafolio(ANA)                     # el refresco reescribe la misma fila
        self.assertEqual(list(self.snapshots.filas), [(1, datetime(2026, 11, 16, 9, 37, tzinfo=timezone.utc))])

    def test_la_caida_maxima_sale_de_la_curva(self):
        self._foto(4, "10400")
        self._foto(1, "10097")
        r = self.servicio.obtener_portafolio(ANA)
        self.assertAlmostEqual(r.caida_maxima, (7000 - 10400) / 10400 * 100)

    def test_si_la_primera_foto_es_anterior_a_la_cuenta_no_se_agrega_el_punto_inicial(self):
        self.cuentas.cuentas[0].creada_en = AHORA - timedelta(hours=1)
        self._foto(1, "10000")
        self.assertEqual(len(self.servicio.obtener_portafolio(ANA).puntos), 2)

    def test_con_poco_historial_no_hay_volatilidad_ni_sharpe(self):
        r = self.servicio.obtener_portafolio(ANA)
        self.assertEqual((r.volatilidad_anual, r.sharpe), (None, None))

    def test_con_mucho_historial_si_los_calcula(self):
        for dias in range(30, 0, -1):
            self._foto(dias, str(10000 + (dias % 3) * 50 - dias * 2))
        r = self.servicio.obtener_portafolio(ANA)
        self.assertIsNotNone(r.volatilidad_anual)
        self.assertIsNotNone(r.sharpe)

    def test_operaciones_estadisticas_y_comisiones(self):
        self.posiciones.cerradas = [_cerrada("30", "2"), _cerrada("-10", "1")]
        r = self.servicio.obtener_portafolio(ANA)
        self.assertEqual(r.pnl_realizado, D("20"))
        self.assertEqual((r.estadisticas.total, r.estadisticas.tasa_aciertos), (2, D("50")))
        self.assertEqual(r.comisiones_pagadas, D("3.9"))          # 2 + 1 de lo cerrado + 0,9 de lo que aún se tiene
        self.assertEqual([o.ganancia_pct for o in r.operaciones], [D("15"), D("-5")])    # 30 y -10 sobre 200

    def test_sin_operaciones(self):
        r = self.servicio.obtener_portafolio(ANA)
        self.assertEqual((r.estadisticas.total, r.operaciones, r.pnl_realizado), (0, [], D("0")))

    def test_el_administrador_y_los_anonimos_no_tienen_portafolio(self):
        for actor in (ADMIN, None):
            with self.assertRaises(ErrorPermisos):
                self.servicio.obtener_portafolio(actor)

    def test_sin_cuenta_simulada(self):
        self.cuentas.cuentas.clear()
        with self.assertRaises(ErrorOperacionInvalida):
            self.servicio.obtener_portafolio(ANA)


if __name__ == "__main__":
    unittest.main()
