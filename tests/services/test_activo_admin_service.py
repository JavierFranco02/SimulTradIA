"""Pruebas de la administración del catálogo de activos y sus fuentes de datos."""
import unittest
from datetime import datetime, timezone
from decimal import Decimal as D

from simultradia.core.exceptions import DatosInvalidos, ErrorOperacionInvalida, ErrorPermisos, ErrorServicioExterno
from simultradia.domain.entities.activo_entity import Activo
from simultradia.domain.entities.cotizacion_entity import Cotizacion
from simultradia.domain.entities.fuente_entity import Fuente
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.domain.entities.vela_entity import Vela
from simultradia.domain.enums import IntervaloVela as I
from simultradia.domain.enums import RolUsuario, TipoActivo
from simultradia.services.activo_admin_service import ActivoAdminService
from tests.fakes import ClienteMercadoFalso, DatabaseFalsa, RepoActivoFalso, RepoFuenteFalso, RepoPrecioFalso

ADMIN = Usuario("Jefe", "j@x.com", "h", rol=RolUsuario.ADMIN, id_usuario=1)
NORMAL = Usuario("Ana", "a@x.com", "h", id_usuario=2)
BINANCE, YAHOO = 1, 2


class PruebasActivoAdminService(unittest.TestCase):
    def setUp(self):
        self.precios = RepoPrecioFalso()
        self.repo = RepoActivoFalso([Activo("BTC/USDT", "Bitcoin", id_activo=1, id_fuente=BINANCE)], self.precios)
        self.binance = ClienteMercadoFalso("Binance", simbolos={"BTC/USDT", "PEPE/USDT"})
        self.yahoo = ClienteMercadoFalso(
            "Yahoo Finance", tipos={TipoActivo.ACCION, TipoActivo.ETF, TipoActivo.DIVISA},
            patron=r"^[A-Z0-9.^=\-]{1,15}$", ejemplo="AAPL", simbolos={"AAPL", "EURUSD=X"})
        fuentes = RepoFuenteFalso([Fuente("Binance", id_fuente=BINANCE), Fuente("Yahoo Finance", id_fuente=YAHOO),
                                   Fuente("Sin cliente", id_fuente=3)])
        self.servicio = ActivoAdminService(DatabaseFalsa(), self.repo, self.precios, fuentes,
                                           {"Binance": self.binance, "Yahoo Finance": self.yahoo})

    def _errores(self, ticker, nombre, tipo="cripto", id_fuente=BINANCE):
        with self.assertRaises(DatosInvalidos) as contexto:
            self.servicio.agregar(ADMIN, ticker, nombre, tipo, id_fuente)
        return contexto.exception.errores

    # ---------------------------------------------------------------- agregar
    def test_agrega_una_cripto_normalizando_el_ticker(self):
        activo = self.servicio.agregar(ADMIN, "  pepe/usdt ", " Pepe ", "cripto", BINANCE)
        self.assertEqual((activo.ticker, activo.nombre, activo.tipo, activo.id_fuente),
                         ("PEPE/USDT", "Pepe", TipoActivo.CRIPTO, BINANCE))
        self.assertEqual((activo.moneda, len(self.repo.activos)), ("USD", 2))

    def test_agrega_una_accion_de_yahoo(self):
        activo = self.servicio.agregar(ADMIN, "aapl", "Apple", "accion", YAHOO)
        self.assertEqual((activo.ticker, activo.tipo, activo.id_fuente), ("AAPL", TipoActivo.ACCION, YAHOO))

    def test_una_divisa_toma_su_moneda_del_ticker(self):
        self.yahoo.simbolos.add("USDJPY=X")
        self.assertEqual(self.servicio.agregar(ADMIN, "USDJPY=X", "Dólar/Yen", "divisa", YAHOO).moneda, "JPY")
        self.assertEqual(self.servicio.agregar(ADMIN, "EURUSD=X", "Euro/Dólar", "divisa", YAHOO).moneda, "USD")

    def test_cada_error_indica_su_campo(self):
        self.assertEqual(list(self._errores("", "Pepe")), ["ticker"])
        self.assertEqual(list(self._errores("PEPE", "Pepe")), ["ticker"])        # no cumple el formato de Binance
        self.assertEqual(list(self._errores("PEPE/USDT", "")), ["nombre"])
        self.assertEqual(sorted(self._errores("mal", "")), ["nombre", "ticker"])
        self.assertEqual(list(self._errores("PEPE/USDT", "Pepe", tipo="inventado")), ["tipo"])
        self.assertEqual(list(self._errores("PEPE/USDT", "Pepe", id_fuente=99)), ["fuente"])

    def test_el_formato_del_ticker_depende_de_la_fuente(self):
        self.assertIn("BTC/USDT", self._errores("AAPL", "Apple", "cripto", BINANCE)["ticker"])    # ejemplo de Binance
        self.assertIn("AAPL", self._errores("PEPE/USDT", "Pepe", "accion", YAHOO)["ticker"])      # ejemplo de Yahoo

    def test_la_fuente_debe_ofrecer_ese_tipo_de_activo(self):
        self.assertIn("Binance no ofrece", self._errores("AAPL", "Apple", "accion", BINANCE)["fuente"])
        self.assertIn("Yahoo Finance no ofrece", self._errores("AAPL", "Apple", "bono", YAHOO)["fuente"])

    def test_una_fuente_sin_cliente_programado_se_rechaza(self):
        self.assertIn("no está programada", self._errores("X", "Xx", "cripto", 3)["fuente"])

    def test_no_se_repite_un_activo_del_catalogo(self):
        self.assertIn("catálogo", self._errores("btc/usdt", "Otro")["ticker"])

    def test_la_fuente_debe_conocer_el_ticker(self):
        self.assertIn("Binance", self._errores("NOEXISTE/USDT", "Xx")["ticker"])
        self.assertEqual(len(self.repo.activos), 1)

    def test_si_la_fuente_no_responde_se_avisa_y_no_se_agrega(self):
        self.binance.error = ErrorServicioExterno("sin internet")
        with self.assertRaises(ErrorServicioExterno):
            self.servicio.agregar(ADMIN, "PEPE/USDT", "Pepe", "cripto", BINANCE)
        self.assertEqual(len(self.repo.activos), 1)

    # ------------------------------------------------------- habilitar / listar
    def test_deshabilitar_y_habilitar(self):
        self.servicio.cambiar_estado(ADMIN, 1, False)
        self.assertFalse(self.repo.activos[0].activo)
        self.servicio.cambiar_estado(ADMIN, 1, True)
        self.assertTrue(self.repo.activos[0].activo)
        with self.assertRaises(ErrorOperacionInvalida):
            self.servicio.cambiar_estado(ADMIN, 99, False)

    def test_listar_incluye_los_deshabilitados(self):
        self.repo.activos[0].activo = False
        self.assertEqual(len(self.servicio.listar(ADMIN)), 1)

    # ---------------------------------------------------------- cambiar fuente
    def _con_accion(self):
        accion = self.repo.insertar(None, Activo("AAPL", "Apple", tipo=TipoActivo.ACCION, id_fuente=YAHOO))
        self.precios.cotizaciones[accion.id_activo] = Cotizacion(precio=D("1"), id_activo=accion.id_activo)
        self.precios.velas[(accion.id_activo, I.H1)] = [Vela(datetime(2026, 1, 1, tzinfo=timezone.utc), D(1), D(1), D(1), D(1), D(1))]
        return accion

    def test_cambiar_la_fuente_borra_las_velas_y_la_cotizacion_guardadas(self):
        accion = self._con_accion()
        self.yahoo.TIPOS = self.yahoo.TIPOS | {TipoActivo.ACCION}
        otra = ClienteMercadoFalso("Otra", tipos={TipoActivo.ACCION}, patron=r"^[A-Z]+$", ejemplo="AAPL", simbolos={"AAPL"})
        servicio = ActivoAdminService(DatabaseFalsa(), self.repo, self.precios,
                                      RepoFuenteFalso([Fuente("Yahoo Finance", id_fuente=YAHOO), Fuente("Otra", id_fuente=3)]),
                                      {"Yahoo Finance": self.yahoo, "Otra": otra})
        servicio.cambiar_fuente(ADMIN, accion.id_activo, 3)
        self.assertEqual(accion.id_fuente, 3)
        self.assertEqual((self.precios.cotizaciones.get(accion.id_activo), self.precios.velas), (None, {}))

    def test_la_nueva_fuente_debe_ofrecer_ese_tipo_y_conocer_el_ticker(self):
        accion = self._con_accion()
        with self.assertRaises(ErrorOperacionInvalida):
            self.servicio.cambiar_fuente(ADMIN, accion.id_activo, BINANCE)        # Binance no tiene acciones
        self.assertEqual(accion.id_fuente, YAHOO)
        with self.assertRaises(ErrorOperacionInvalida):
            self.servicio.cambiar_fuente(ADMIN, 99, YAHOO)                        # el activo no existe

    def test_elegir_la_misma_fuente_no_borra_nada(self):
        accion = self._con_accion()
        self.servicio.cambiar_fuente(ADMIN, accion.id_activo, YAHOO)
        self.assertIn(accion.id_activo, self.precios.cotizaciones)

    # ------------------------------------------------------- buscar y filtrar
    def _con_varios(self):
        self.repo.insertar(None, Activo("AAPL", "Apple", tipo=TipoActivo.ACCION, id_fuente=YAHOO))
        self.repo.insertar(None, Activo("OLD/USDT", "Viejo", activo=False, id_fuente=BINANCE))

    def test_buscar_por_ticker_o_nombre(self):
        self._con_varios()
        self.assertEqual([i.activo.ticker for i in self.servicio.listar(ADMIN, texto=" aap ")], ["AAPL"])
        self.assertEqual([i.activo.ticker for i in self.servicio.listar(ADMIN, texto="bitco")], ["BTC/USDT"])

    def test_filtrar_por_tipo_y_por_estado(self):
        self._con_varios()
        self.assertEqual([i.activo.ticker for i in self.servicio.listar(ADMIN, tipo="accion")], ["AAPL"])
        self.assertEqual([i.activo.ticker for i in self.servicio.listar(ADMIN, habilitado=False)], ["OLD/USDT"])
        self.assertEqual(len(self.servicio.listar(ADMIN, habilitado=True)), 2)
        self.assertEqual(len(self.servicio.listar(ADMIN)), 3)                    # sin filtros: todo, deshabilitados incluidos
        self.assertEqual([i.activo.ticker for i in self.servicio.listar(ADMIN, texto="usdt", habilitado=True)], ["BTC/USDT"])

    # ---------------------------------------------------------------- editar
    def test_editar_el_nombre_y_la_moneda(self):
        self.servicio.editar(ADMIN, 1, "  Bitcoin (BTC) ", "usd")
        self.assertEqual((self.repo.activos[0].nombre, self.repo.activos[0].moneda), ("Bitcoin (BTC)", "USD"))
        self.assertEqual(self.repo.activos[0].ticker, "BTC/USDT")                # el ticker no se toca

    def test_editar_valida_cada_campo(self):
        for nombre, moneda, campo in (("", "USD", "nombre"), ("B", "USD", "nombre"), ("Bitcoin", "", "moneda"),
                                      ("Bitcoin", "DOLAR", "moneda"), ("Bitcoin", "U5D", "moneda")):
            with self.subTest(nombre=nombre, moneda=moneda):
                with self.assertRaises(DatosInvalidos) as contexto:
                    self.servicio.editar(ADMIN, 1, nombre, moneda)
                self.assertEqual(list(contexto.exception.errores), [campo])
        with self.assertRaises(DatosInvalidos) as contexto:
            self.servicio.editar(ADMIN, 1, "", "x")
        self.assertEqual(sorted(contexto.exception.errores), ["moneda", "nombre"])
        self.assertEqual(self.repo.activos[0].nombre, "Bitcoin")

    def test_editar_un_activo_inexistente(self):
        with self.assertRaises(ErrorOperacionInvalida):
            self.servicio.editar(ADMIN, 99, "Algo", "USD")

    # ---------------------------------------------------------- probar ticker
    def test_probar_un_ticker_que_la_fuente_reconoce_no_guarda_nada(self):
        self.assertEqual(self.servicio.probar_ticker(ADMIN, " pepe/usdt ", "cripto", BINANCE), "Binance")
        self.assertEqual(self.servicio.probar_ticker(ADMIN, "aapl", "accion", YAHOO), "Yahoo Finance")
        self.assertEqual(len(self.repo.activos), 1)

    def test_probar_un_ticker_con_problemas_dice_el_motivo(self):
        with self.assertRaises(DatosInvalidos) as c:
            self.servicio.probar_ticker(ADMIN, "NOEXISTE/USDT", "cripto", BINANCE)
        self.assertIn("Binance no tiene ese ticker", c.exception.errores["ticker"])
        with self.assertRaises(DatosInvalidos) as c:
            self.servicio.probar_ticker(ADMIN, "AAPL", "accion", BINANCE)
        self.assertIn("Binance no ofrece", c.exception.errores["fuente"])
        with self.assertRaises(DatosInvalidos) as c:
            self.servicio.probar_ticker(ADMIN, "", "cripto", BINANCE)
        self.assertEqual(list(c.exception.errores), ["ticker"])

    def test_si_la_fuente_no_responde_al_probar_se_avisa(self):
        self.binance.error = ErrorServicioExterno("sin internet")
        with self.assertRaises(ErrorServicioExterno):
            self.servicio.probar_ticker(ADMIN, "BTC/USDT", "cripto", BINANCE)

    def test_probar_exige_administrador_y_editar_tambien(self):
        for actor in (NORMAL, None):
            with self.assertRaises(ErrorPermisos):
                self.servicio.probar_ticker(actor, "BTC/USDT", "cripto", BINANCE)
            with self.assertRaises(ErrorPermisos):
                self.servicio.editar(actor, 1, "Otro", "USD")
        self.assertEqual(self.repo.activos[0].nombre, "Bitcoin")

    # ---------------------------------------------------------------- permisos
    def test_todo_exige_administrador(self):
        for actor in (NORMAL, None):
            for llamada in (lambda a: self.servicio.listar(a),
                            lambda a: self.servicio.agregar(a, "PEPE/USDT", "Pepe", "cripto", BINANCE),
                            lambda a: self.servicio.cambiar_estado(a, 1, False),
                            lambda a: self.servicio.cambiar_fuente(a, 1, YAHOO)):
                with self.assertRaises(ErrorPermisos):
                    llamada(actor)
        self.assertEqual(len(self.repo.activos), 1)


if __name__ == "__main__":
    unittest.main()
