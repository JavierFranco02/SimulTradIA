"""Pruebas de los controladores de administración, con vista y servicios FALSOS."""
import unittest
from decimal import Decimal as D
from unittest import mock

from simultradia.core.exceptions import DatosInvalidos, ErrorOperacionInvalida
from simultradia.core.session import Session
from simultradia.domain.entities.activo_entity import Activo
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.domain.enums import RolUsuario
from simultradia.iu.admin.activos_controller import ActivosAdminController
from simultradia.iu.admin.ingesta_controller import IngestaController
from simultradia.iu.admin.usuarios_controller import UsuariosController
from simultradia.services.ingesta_service import ResultadoIngesta
from tests.fakes import ServicioGenerico, VistaPanelFalsa, en_el_acto

_HILO = "simultradia.iu.base.panel_controller.ejecutar_en_hilo"


def _sesion():
    sesion = Session()
    sesion.iniciar(Usuario("Jefe", "j@x.com", "h", rol=RolUsuario.ADMIN, id_usuario=1))
    return sesion


class _Base(unittest.TestCase):
    def setUp(self):
        parche = mock.patch(_HILO, en_el_acto)
        parche.start()
        self.addCleanup(parche.stop)
        self.sesion = _sesion()


class PruebasUsuariosController(_Base):
    def test_cargar_lista_con_el_administrador_como_actor(self):
        vista, servicio = VistaPanelFalsa(), ServicioGenerico(listar=["U1", "U2"])
        UsuariosController(vista, servicio, self.sesion).cargar()
        self.assertEqual(servicio.llamadas, [("listar", self.sesion.usuario, "", None, None)])
        self.assertEqual(vista.ultimo("usuarios"), ["U1", "U2"])

    def test_los_filtros_de_la_vista_se_envian_al_servicio(self):
        vista, servicio = VistaPanelFalsa(), ServicioGenerico(listar=[])
        vista.filtros_ = ("ana", "admin", True)
        UsuariosController(vista, servicio, self.sesion)
        vista.acciones["al_filtrar"]()
        self.assertEqual(servicio.llamadas[-1], ("listar", self.sesion.usuario, "ana", "admin", True))

    def test_una_respuesta_vieja_de_la_busqueda_se_descarta(self):
        from tests.fakes import EjecutorDiferido
        vista, servicio = VistaPanelFalsa(), ServicioGenerico(listar=["U"])
        controlador = UsuariosController(vista, servicio, self.sesion)
        ejecutor = EjecutorDiferido()
        with mock.patch(_HILO, ejecutor):
            controlador.cargar()
            controlador.cargar()
            ejecutor.terminar_todo()
        self.assertEqual(len([e for e in vista.eventos if e[0] == "usuarios"]), 1)

    def test_restablecer_la_contrasena_pide_confirmacion_muestra_la_temporal_y_recarga(self):
        vista, servicio = VistaPanelFalsa(confirma=True), ServicioGenerico(restablecer_password="Abc23xyz45", listar=[])
        UsuariosController(vista, servicio, self.sesion)
        vista.acciones["al_restablecer"](3)
        self.assertEqual(servicio.llamadas[0], ("restablecer_password", self.sesion.usuario, 3))
        self.assertEqual(vista.ultimo("temporal"), (3, "Abc23xyz45"))
        self.assertEqual(servicio.llamadas[-1][0], "listar")

    def test_si_no_se_confirma_no_se_restablece_nada(self):
        vista, servicio = VistaPanelFalsa(confirma=False), ServicioGenerico()
        UsuariosController(vista, servicio, self.sesion)
        vista.acciones["al_restablecer"](3)
        self.assertEqual(servicio.llamadas, [])
        self.assertIsNone(vista.ultimo("temporal"))

    def test_un_error_al_restablecer_se_muestra_y_no_se_revela_ninguna_contrasena(self):
        vista = VistaPanelFalsa()
        servicio = ServicioGenerico(restablecer_password=ErrorOperacionInvalida("No se puede restablecer la contraseña de un administrador desde aquí."))
        UsuariosController(vista, servicio, self.sesion)
        vista.acciones["al_restablecer"](2)
        self.assertIn("administrador", vista.error)
        self.assertIsNone(vista.ultimo("temporal"))

    def test_desactivar_pide_confirmacion_y_recarga(self):
        vista, servicio = VistaPanelFalsa(confirma=True), ServicioGenerico(listar=[])
        UsuariosController(vista, servicio, self.sesion)
        vista.acciones["al_cambiar_estado"](3, False)
        self.assertEqual(servicio.llamadas[0], ("cambiar_estado", self.sesion.usuario, 3, False))
        self.assertEqual(servicio.llamadas[-1][0], "listar")

    def test_si_no_se_confirma_no_se_hace_nada(self):
        vista, servicio = VistaPanelFalsa(confirma=False), ServicioGenerico()
        UsuariosController(vista, servicio, self.sesion)
        vista.acciones["al_cambiar_estado"](3, False)
        self.assertEqual(servicio.llamadas, [])

    def test_reactivar_no_pide_confirmacion(self):
        vista, servicio = VistaPanelFalsa(confirma=False), ServicioGenerico(listar=[])
        UsuariosController(vista, servicio, self.sesion)
        vista.acciones["al_cambiar_estado"](3, True)
        self.assertEqual(servicio.llamadas[0][0], "cambiar_estado")

    def test_un_error_del_servicio_se_muestra(self):
        vista = VistaPanelFalsa()
        servicio = ServicioGenerico(cambiar_estado=ErrorOperacionInvalida("No puedes desactivar tu propia cuenta."))
        UsuariosController(vista, servicio, self.sesion)
        vista.acciones["al_cambiar_estado"](1, False)
        self.assertEqual(vista.error, "No puedes desactivar tu propia cuenta.")


class PruebasActivosAdminController(_Base):
    def _crear(self, activos_extra=None, **servicio):
        vista = VistaPanelFalsa(valores={"ticker": "aapl", "nombre": "Apple", "tipo": "accion", "fuente": "2"})
        servicio = ServicioGenerico(**servicio)
        fuentes = ServicioGenerico(listar=["F1", "F2"])
        return vista, servicio, fuentes, ActivosAdminController(vista, servicio, fuentes, self.sesion)

    def test_cargar_llena_la_tabla_y_las_fuentes(self):
        vista, _, _, controlador = self._crear(listar=["A1"])
        controlador.cargar()
        self.assertEqual(vista.ultimo("activos"), ["A1"])
        self.assertEqual(vista.ultimo("fuentes"), ["F1", "F2"])

    def test_agregar_correcto_envia_todos_los_campos_limpia_y_recarga(self):
        vista, servicio, _, _ = self._crear(agregar=Activo("AAPL", "Apple"), listar=[])
        vista.acciones["al_agregar"]()
        self.assertEqual(servicio.llamadas[0], ("agregar", self.sesion.usuario, "aapl", "Apple", "accion", 2))
        self.assertFalse(vista.ocupado)
        self.assertIsNotNone(vista.ultimo("limpiar_formulario"))
        self.assertIn("AAPL", vista.exito)
        self.assertEqual(servicio.llamadas[-1][0], "listar")

    def test_los_errores_de_campo_van_cada_uno_a_su_campo(self):
        vista, *_ = self._crear(agregar=DatosInvalidos({"ticker": "Yahoo Finance no tiene ese ticker."}))
        vista.acciones["al_agregar"]()
        self.assertEqual(vista.ultimo("errores_campos"), {"ticker": "Yahoo Finance no tiene ese ticker."})
        self.assertFalse(vista.ocupado)
        self.assertIsNone(vista.error)

    def test_ignora_pulsaciones_mientras_esta_ocupado(self):
        vista, servicio, *_ = self._crear(agregar=None)
        vista.ocupado = True
        vista.acciones["al_agregar"]()
        self.assertEqual(servicio.llamadas, [])

    def test_habilitar_o_deshabilitar_recarga_la_lista(self):
        vista, servicio, *_ = self._crear(listar=[])
        vista.acciones["al_cambiar_estado"](4, False)
        self.assertEqual(servicio.llamadas[0], ("cambiar_estado", self.sesion.usuario, 4, False))
        self.assertEqual(servicio.llamadas[-1][0], "listar")

    def test_los_filtros_se_envian_al_listar(self):
        vista, servicio, *_ = self._crear(listar=[])
        vista.filtros_ = ("btc", "cripto", False)
        vista.acciones["al_filtrar"]()
        self.assertEqual(servicio.llamadas[-1], ("listar", self.sesion.usuario, "btc", "cripto", False))

    def test_editar_guarda_y_recarga(self):
        vista, servicio, *_ = self._crear(listar=[])
        vista.acciones["al_editar"](4, "Bitcoin (BTC)", "usd")
        self.assertEqual(servicio.llamadas[0], ("editar", self.sesion.usuario, 4, "Bitcoin (BTC)", "usd"))
        self.assertEqual(vista.exito, "Cambios guardados.")
        self.assertEqual(servicio.llamadas[-1][0], "listar")

    def test_los_errores_de_la_edicion_van_a_sus_campos(self):
        vista, *_ = self._crear(editar=DatosInvalidos({"moneda": "Usa un código de 3 letras, por ejemplo USD."}))
        vista.acciones["al_editar"](4, "Bitcoin", "xx")
        self.assertEqual(vista.ultimo("errores_edicion"), {"moneda": "Usa un código de 3 letras, por ejemplo USD."})
        self.assertIsNone(vista.error)

    def test_probar_un_ticker_avisa_que_la_fuente_lo_reconoce_y_no_agrega_nada(self):
        vista, servicio, *_ = self._crear(probar_ticker="Yahoo Finance")
        vista.acciones["al_probar_ticker"]()
        self.assertEqual(servicio.llamadas, [("probar_ticker", self.sesion.usuario, "aapl", "accion", 2)])
        self.assertIn("Yahoo Finance reconoce AAPL", vista.exito)
        self.assertFalse(vista.ocupado)

    def test_probar_un_ticker_que_la_fuente_no_conoce_marca_el_campo(self):
        vista, *_ = self._crear(probar_ticker=DatosInvalidos({"ticker": "Yahoo Finance no tiene ese ticker."}))
        vista.acciones["al_probar_ticker"]()
        self.assertEqual(vista.ultimo("errores_campos"), {"ticker": "Yahoo Finance no tiene ese ticker."})
        self.assertFalse(vista.ocupado)

    def test_probar_la_fuente_de_un_activo_elegido(self):
        vista, servicio, *_ = self._crear(probar_ticker="Binance")
        vista.acciones["al_probar_fuente"]("BTC/USDT", "cripto", 1)
        self.assertEqual(servicio.llamadas, [("probar_ticker", self.sesion.usuario, "BTC/USDT", "cripto", 1)])
        self.assertIn("Binance reconoce BTC/USDT", vista.exito)

    def test_probar_una_fuente_que_no_ofrece_ese_tipo_va_al_mensaje_general(self):
        vista, *_ = self._crear(probar_ticker=DatosInvalidos({"fuente": "Binance no ofrece ese tipo de activo."}))
        vista.acciones["al_probar_fuente"]("AAPL", "accion", 1)
        self.assertEqual(vista.error, "Binance no ofrece ese tipo de activo.")
        self.assertIsNone(vista.ultimo("errores_campos"))

    def test_cambiar_la_fuente_pide_confirmacion(self):
        vista, servicio, *_ = self._crear(listar=[])
        vista.acciones["al_cambiar_fuente"](4, 2)
        self.assertEqual(servicio.llamadas[0], ("cambiar_fuente", self.sesion.usuario, 4, 2))
        self.assertEqual(servicio.llamadas[-1][0], "listar")
        vista._confirma = False
        servicio.llamadas.clear()
        vista.acciones["al_cambiar_fuente"](4, 2)
        self.assertEqual(servicio.llamadas, [])

    def test_un_error_al_cambiar_la_fuente_se_muestra(self):
        vista, *_ = self._crear(cambiar_fuente=ErrorOperacionInvalida("Binance no ofrece ese tipo de activo."))
        vista.acciones["al_cambiar_fuente"](4, 1)
        self.assertEqual(vista.error, "Binance no ofrece ese tipo de activo.")


class PruebasIngestaController(_Base):
    def _crear(self, **ingesta):
        vista = VistaPanelFalsa()
        servicio, fuentes = ServicioGenerico(**ingesta), ServicioGenerico(listar=["F1"], cambiar_estado=None)
        return vista, servicio, fuentes, IngestaController(vista, servicio, fuentes, self.sesion)

    def test_cargar_muestra_el_estado_con_las_fuentes_y_se_refresca_cada_5_segundos(self):
        vista, _, _, controlador = self._crear(obtener_estado="ESTADO")
        controlador.cargar()
        self.assertEqual(vista.ultimo("estado"), ("ESTADO", ["F1"]))
        self.assertEqual([ms for ms, _ in vista.programadas], [5000])

    def test_actualizacion_manual_correcta(self):
        vista, *_ = self._crear(ejecutar_manual=ResultadoIngesta(62, []), obtener_estado="E")
        vista.acciones["al_actualizar"]()
        self.assertIn("62", vista.exito)
        self.assertFalse(vista.ocupado)

    def test_actualizacion_manual_con_errores_los_lista(self):
        vista, *_ = self._crear(ejecutar_manual=ResultadoIngesta(1, ["ETH/USDT 1h"]), obtener_estado="E")
        vista.acciones["al_actualizar"]()
        self.assertIn("ETH/USDT 1h", vista.error)

    def test_si_la_actualizacion_falla_se_libera_el_boton(self):
        vista, *_ = self._crear(ejecutar_manual=ErrorOperacionInvalida("sin internet"))
        vista.acciones["al_actualizar"]()
        self.assertEqual((vista.error, vista.ocupado), ("sin internet", False))

    def test_ignora_pulsaciones_mientras_esta_ocupado(self):
        vista, servicio, *_ , controlador = self._crear()
        vista.ocupado = True
        controlador.actualizar_ahora()
        self.assertEqual(servicio.llamadas, [])

    def test_probar_la_conexion_de_una_fuente(self):
        from simultradia.services.ingesta_service import ResultadoPrueba
        vista, servicio, *_ = self._crear(probar_fuente=ResultadoPrueba("Binance", True, 320, "Responde con datos."))
        vista.acciones["al_probar_fuente"](1)
        self.assertEqual(servicio.llamadas, [("probar_fuente", self.sesion.usuario, 1)])
        self.assertEqual(vista.exito, "Binance: Responde con datos. (320 ms)")
        self.assertFalse(vista.ocupado)

    def test_una_fuente_que_no_responde_se_muestra_como_error(self):
        from simultradia.services.ingesta_service import ResultadoPrueba
        vista, *_ = self._crear(probar_fuente=ResultadoPrueba("Yahoo Finance", False, 5000, "sin internet"))
        vista.acciones["al_probar_fuente"](2)
        self.assertEqual(vista.error, "Yahoo Finance no responde: sin internet")
        self.assertFalse(vista.ocupado)

    def test_actualizar_solo_una_fuente(self):
        vista, servicio, *_ = self._crear(ejecutar_manual=ResultadoIngesta(31, []), obtener_estado="E")
        vista.acciones["al_actualizar_fuente"](2)
        self.assertEqual(servicio.llamadas[0], ("ejecutar_manual", self.sesion.usuario, 2))
        self.assertIn("31", vista.exito)

    def test_actualizar_o_probar_una_fuente_se_ignora_si_ya_hay_algo_corriendo(self):
        vista, servicio, *_ = self._crear()
        vista.ocupado = True
        vista.acciones["al_actualizar_fuente"](1)
        vista.acciones["al_probar_fuente"](1)
        self.assertEqual(servicio.llamadas, [])

    def test_un_error_al_actualizar_una_fuente_deshabilitada_se_muestra(self):
        vista, *_ = self._crear(ejecutar_manual=ErrorOperacionInvalida("Esa fuente está deshabilitada: habilítala para actualizarla."))
        vista.acciones["al_actualizar_fuente"](2)
        self.assertIn("deshabilitada", vista.error)
        self.assertFalse(vista.ocupado)

    def test_deshabilitar_una_fuente_pide_confirmacion_y_refresca_el_estado(self):
        vista, servicio, fuentes, _ = self._crear(obtener_estado="E")
        vista.acciones["al_cambiar_fuente"](2, False)
        self.assertEqual(fuentes.llamadas[0], ("cambiar_estado", self.sesion.usuario, 2, False))
        self.assertEqual(vista.ultimo("estado"), ("E", ["F1"]))
        vista._confirma = False
        fuentes.llamadas.clear()
        vista.acciones["al_cambiar_fuente"](2, False)
        self.assertEqual(fuentes.llamadas, [])

    def test_habilitar_una_fuente_no_pide_confirmacion(self):
        vista, _, fuentes, _ = self._crear(obtener_estado="E")
        vista._confirma = False
        vista.acciones["al_cambiar_fuente"](2, True)
        self.assertEqual(fuentes.llamadas[0][0], "cambiar_estado")


if __name__ == "__main__":
    unittest.main()
