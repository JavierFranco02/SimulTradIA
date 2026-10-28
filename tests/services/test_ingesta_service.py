"""Pruebas de la ingesta: varias fuentes, ritmo de cada una, velas y permisos del administrador."""
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

from simultradia.core.exceptions import ErrorOperacionInvalida, ErrorPermisos, ErrorServicioExterno
from simultradia.domain.entities.activo_entity import Activo
from simultradia.domain.entities.cotizacion_entity import Cotizacion
from simultradia.domain.entities.fuente_entity import Fuente
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.domain.entities.vela_entity import Vela
from simultradia.domain.enums import IntervaloVela as I
from simultradia.domain.enums import RolUsuario, TipoActivo
from simultradia.domain.reglas.intervalos import GUARDADOS
from simultradia.services.ingesta_service import IngestaService
from tests.fakes import (
    ClienteMercadoFalso, DatabaseFalsa, RepoActivoFalso, RepoFuenteFalso, RepoPrecioFalso)

ADMIN = Usuario("Jefe", "j@x.com", "h", rol=RolUsuario.ADMIN, id_usuario=1)
NORMAL = Usuario("Ana", "a@x.com", "h", id_usuario=2)


class Reloj:
    def __init__(self): self.ahora = 1000.0
    def __call__(self): return self.ahora


def _montar(binance=None, yahoo=None, activos=None, fuentes=None):
    precios = RepoPrecioFalso()
    activos = activos if activos is not None else [
        Activo("BTC/USDT", "Bitcoin", id_activo=1, id_fuente=1),
        Activo("ETH/USDT", "Ethereum", id_activo=2, id_fuente=1),
        Activo("AAPL", "Apple", tipo=TipoActivo.ACCION, id_activo=3, id_fuente=2)]
    fuentes = fuentes if fuentes is not None else [Fuente("Binance", id_fuente=1), Fuente("Yahoo Finance", id_fuente=2)]
    binance = binance or ClienteMercadoFalso("Binance")
    yahoo = yahoo or ClienteMercadoFalso("Yahoo Finance", segundos_cotizaciones=30, segundos_velas=300)
    reloj = Reloj()
    servicio = IngestaService(DatabaseFalsa(), RepoActivoFalso(activos, precios), precios,
                              RepoFuenteFalso(fuentes), {"Binance": binance, "Yahoo Finance": yahoo}, reloj)
    return servicio, precios, binance, yahoo, reloj


def _vela(momento):
    return Vela(momento, D(1), D(2), D(1), D(2), D(1))


class PruebasCotizaciones(unittest.TestCase):
    def test_cada_activo_se_pide_a_su_fuente_y_se_guarda_con_su_id(self):
        binance = ClienteMercadoFalso("Binance", cotizaciones={"BTC/USDT": Cotizacion(precio=D("60000")),
                                                               "ETH/USDT": Cotizacion(precio=D("3000"))})
        yahoo = ClienteMercadoFalso("Yahoo Finance", cotizaciones={"AAPL": Cotizacion(precio=D("230"))})
        servicio, precios, _b, _y, _r = _montar(binance, yahoo)
        resultado = servicio.actualizar_cotizaciones()
        self.assertEqual((resultado.correctos, resultado.fallidos), (3, []))
        self.assertEqual(binance.pedidos_cotizaciones, [["BTC/USDT", "ETH/USDT"]])
        self.assertEqual(yahoo.pedidos_cotizaciones, [["AAPL"]])
        self.assertEqual({i: c.precio for i, c in precios.cotizaciones.items()},
                         {1: D("60000"), 2: D("3000"), 3: D("230")})

    def test_los_que_la_fuente_no_devuelve_quedan_como_fallidos(self):
        binance = ClienteMercadoFalso("Binance", cotizaciones={"BTC/USDT": Cotizacion(precio=D("1"))})
        servicio, precios, *_ = _montar(binance)
        resultado = servicio.actualizar_cotizaciones()
        self.assertEqual(sorted(resultado.fallidos), ["AAPL", "ETH/USDT"])
        self.assertEqual(list(precios.cotizaciones), [1])

    def test_si_una_fuente_falla_las_demas_siguen(self):
        yahoo_caido = ClienteMercadoFalso("Yahoo Finance", error=ErrorServicioExterno("sin internet"))
        binance = ClienteMercadoFalso("Binance", cotizaciones={"BTC/USDT": Cotizacion(precio=D("1")),
                                                               "ETH/USDT": Cotizacion(precio=D("2"))})
        servicio, precios, *_ = _montar(binance, yahoo_caido)
        resultado = servicio.actualizar_cotizaciones()
        self.assertEqual((resultado.correctos, resultado.fallidos), (2, ["AAPL"]))
        self.assertEqual(sorted(precios.cotizaciones), [1, 2])

    def test_cada_fuente_respeta_su_ritmo(self):
        servicio, _p, binance, yahoo, reloj = _montar()
        servicio.actualizar_cotizaciones()
        reloj.ahora += 2.5                           # a Binance ya le toca (2 s); a Yahoo no (30 s)
        servicio.actualizar_cotizaciones()
        self.assertEqual((len(binance.pedidos_cotizaciones), len(yahoo.pedidos_cotizaciones)), (2, 1))
        reloj.ahora += 30
        servicio.actualizar_cotizaciones()
        self.assertEqual((len(binance.pedidos_cotizaciones), len(yahoo.pedidos_cotizaciones)), (3, 2))

    def test_forzar_ignora_el_ritmo(self):
        servicio, _p, binance, yahoo, _r = _montar()
        servicio.actualizar_cotizaciones()
        servicio.actualizar_cotizaciones(forzar=True)
        self.assertEqual((len(binance.pedidos_cotizaciones), len(yahoo.pedidos_cotizaciones)), (2, 2))

    def test_una_fuente_deshabilitada_no_se_consulta(self):
        servicio, _p, binance, yahoo, _r = _montar(fuentes=[Fuente("Binance", id_fuente=1),
                                                            Fuente("Yahoo Finance", activa=False, id_fuente=2)])
        servicio.actualizar_cotizaciones()
        self.assertEqual((len(binance.pedidos_cotizaciones), len(yahoo.pedidos_cotizaciones)), (1, 0))

    def test_una_fuente_sin_cliente_programado_se_ignora(self):
        servicio, _p, binance, yahoo, _r = _montar(fuentes=[Fuente("Binance", id_fuente=1),
                                                            Fuente("Fuente Nueva", id_fuente=2)])
        self.assertEqual(servicio.actualizar_cotizaciones().correctos, 0)   # nadie devolvió precios, y no falla

    def test_sin_activos_no_llama_a_nadie(self):
        servicio, _p, binance, yahoo, _r = _montar(activos=[])
        self.assertEqual(servicio.actualizar_cotizaciones().correctos, 0)
        self.assertEqual((binance.pedidos_cotizaciones, yahoo.pedidos_cotizaciones), ([], []))


class PruebasVelas(unittest.TestCase):
    def test_la_primera_vez_pide_todo_el_historial_de_cada_intervalo(self):
        servicio, _p, binance, _y, _r = _montar(activos=[Activo("BTC/USDT", "Bitcoin", id_activo=1, id_fuente=1)])
        resultado = servicio.actualizar_velas()
        self.assertEqual(resultado.correctos, len(GUARDADOS))
        pedidos = {intervalo: desde for _t, intervalo, desde in binance.pedidos_velas}
        self.assertEqual(set(pedidos), set(GUARDADOS))
        ahora = datetime.now(timezone.utc)
        for intervalo, dias in GUARDADOS.items():
            self.assertAlmostEqual((ahora - pedidos[intervalo]).total_seconds(), dias * 86400, delta=60)

    def test_las_siguientes_veces_pide_solo_lo_que_falta(self):
        ultima = datetime(2026, 10, 25, 10, 0, tzinfo=timezone.utc)
        binance = ClienteMercadoFalso("Binance", velas={("BTC/USDT", I.H1): [_vela(ultima), _vela(ultima + timedelta(hours=1))]})
        servicio, precios, *_ = _montar(binance, activos=[Activo("BTC/USDT", "Bitcoin", id_activo=1, id_fuente=1)])
        precios.velas[(1, I.H1)] = [_vela(ultima)]
        servicio.actualizar_velas()
        desde = next(d for _t, i, d in binance.pedidos_velas if i == I.H1)
        self.assertEqual(desde, ultima - timedelta(hours=2))     # 2 periodos antes de la última
        self.assertEqual(len(precios.velas[(1, I.H1)]), 2)       # la vela repetida se reemplazó, no se duplicó

    def test_un_error_con_un_activo_no_detiene_a_los_demas(self):
        class BinanceQueFallaConETH(ClienteMercadoFalso):
            def obtener_velas(self, ticker, intervalo, desde):
                if ticker == "ETH/USDT":
                    raise ErrorServicioExterno("falló")
                return super().obtener_velas(ticker, intervalo, desde)

        servicio, *_ = _montar(BinanceQueFallaConETH("Binance"))
        resultado = servicio.actualizar_velas()
        self.assertEqual(resultado.correctos, 2 * len(GUARDADOS))      # BTC y AAPL
        self.assertEqual(len(resultado.fallidos), len(GUARDADOS))
        self.assertTrue(all(f.startswith("ETH/USDT") for f in resultado.fallidos))

    def test_las_velas_tambien_respetan_el_ritmo_de_cada_fuente(self):
        servicio, _p, binance, yahoo, reloj = _montar()
        servicio.actualizar_velas()
        reloj.ahora += 61                              # Binance (60 s) sí; Yahoo (300 s) no
        servicio.actualizar_velas()
        self.assertEqual((len(binance.pedidos_velas), len(yahoo.pedidos_velas)),
                         (4 * len(GUARDADOS), 2 * len(GUARDADOS) - len(GUARDADOS)))


class PruebasUnaFuente(unittest.TestCase):
    def test_actualizar_solo_una_fuente_no_toca_a_las_demas(self):
        servicio, precios, binance, yahoo, _r = _montar()
        resultado = servicio.ejecutar_manual(ADMIN, id_fuente=2)           # Yahoo
        self.assertEqual((len(binance.pedidos_cotizaciones), len(binance.pedidos_velas)), (0, 0))
        self.assertEqual(yahoo.pedidos_cotizaciones, [["AAPL"]])
        self.assertEqual(len(yahoo.pedidos_velas), len(GUARDADOS))
        self.assertEqual(resultado.correctos, len(GUARDADOS))              # sin cotizaciones preparadas: solo velas

    def test_una_fuente_deshabilitada_o_inexistente_no_se_actualiza(self):
        servicio, _p, binance, yahoo, _r = _montar(fuentes=[Fuente("Binance", id_fuente=1),
                                                            Fuente("Yahoo Finance", activa=False, id_fuente=2)])
        with self.assertRaises(ErrorOperacionInvalida):
            servicio.ejecutar_manual(ADMIN, id_fuente=2)
        with self.assertRaises(ErrorOperacionInvalida):
            servicio.ejecutar_manual(ADMIN, id_fuente=99)
        self.assertEqual((yahoo.pedidos_cotizaciones, yahoo.pedidos_velas), ([], []))

    def test_probar_la_conexion_de_una_fuente_que_responde(self):
        yahoo = ClienteMercadoFalso("Yahoo Finance", ejemplo="AAPL", cotizaciones={"AAPL": Cotizacion(precio=D("230"))})
        servicio, _p, _b, yahoo, reloj = _montar(yahoo=yahoo)
        resultado = servicio.probar_fuente(ADMIN, 2)
        self.assertEqual((resultado.fuente, resultado.ok), ("Yahoo Finance", True))
        self.assertEqual(yahoo.pedidos_cotizaciones, [["AAPL"]])             # pide solo el activo de ejemplo
        self.assertEqual(yahoo.pedidos_velas, [])

    def test_probar_no_guarda_nada(self):
        servicio, precios, *_ = _montar()
        servicio.probar_fuente(ADMIN, 1)
        self.assertEqual((precios.cotizaciones, precios.velas), ({}, {}))

    def test_una_fuente_caida_se_informa_como_resultado_no_como_error(self):
        servicio, *_ = _montar(binance=ClienteMercadoFalso("Binance", error=ErrorServicioExterno("sin internet")))
        resultado = servicio.probar_fuente(ADMIN, 1)
        self.assertEqual((resultado.ok, resultado.mensaje), (False, "sin internet"))

    def test_una_fuente_que_responde_sin_datos_no_cuenta_como_ok(self):
        servicio, *_ = _montar()                                  # el falso no tiene cotizaciones preparadas
        resultado = servicio.probar_fuente(ADMIN, 1)
        self.assertFalse(resultado.ok)
        self.assertIn("sin datos", resultado.mensaje)

    def test_probar_una_fuente_inexistente_o_sin_cliente(self):
        servicio, *_ = _montar(fuentes=[Fuente("Binance", id_fuente=1), Fuente("Otra", id_fuente=2)])
        with self.assertRaises(ErrorOperacionInvalida):
            servicio.probar_fuente(ADMIN, 99)
        with self.assertRaises(ErrorOperacionInvalida):
            servicio.probar_fuente(ADMIN, 2)

    def test_probar_y_actualizar_una_fuente_exigen_administrador(self):
        servicio, _p, binance, *_ = _montar()
        for actor in (NORMAL, None):
            with self.assertRaises(ErrorPermisos):
                servicio.probar_fuente(actor, 1)
            with self.assertRaises(ErrorPermisos):
                servicio.ejecutar_manual(actor, 1)
        self.assertEqual(binance.pedidos_cotizaciones, [])


class PruebasAdministrador(unittest.TestCase):
    def test_estado_y_ejecucion_manual_exigen_administrador(self):
        servicio, *_ = _montar()
        for metodo in (servicio.obtener_estado, servicio.ejecutar_manual):
            with self.subTest(metodo=metodo.__name__):
                with self.assertRaises(ErrorPermisos):
                    metodo(NORMAL)
                with self.assertRaises(ErrorPermisos):
                    metodo(None)

    def test_estado(self):
        servicio, precios, *_ = _montar()
        precios.velas[(1, I.H1)] = [_vela(datetime(2026, 1, 1, tzinfo=timezone.utc))]
        precios.ultima = datetime(2026, 10, 25, tzinfo=timezone.utc)
        estado = servicio.obtener_estado(ADMIN)
        self.assertEqual((estado.activos_habilitados, estado.velas_por_intervalo, estado.ultima_cotizacion),
                         (3, {"1h": 1}, precios.ultima))

    def test_ejecucion_manual_suma_cotizaciones_y_velas_sin_esperar_el_ritmo(self):
        servicio, _p, binance, yahoo, _r = _montar()
        servicio.actualizar_cotizaciones()                # ya se consultó hace un instante
        resultado = servicio.ejecutar_manual(ADMIN)
        self.assertEqual(len(binance.pedidos_cotizaciones), 2)
        self.assertEqual(len(yahoo.pedidos_cotizaciones), 2)
        self.assertEqual(resultado.correctos, 0 + 3 * len(GUARDADOS))   # las cotizaciones vacías no suman


if __name__ == "__main__":
    unittest.main()
