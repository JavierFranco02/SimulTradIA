"""Pruebas del controlador de Operar, con vista y servicios FALSOS."""
import unittest
from decimal import Decimal as D
from unittest import mock

from simultradia.core.exceptions import DatosInvalidos, ErrorOperacionInvalida
from simultradia.core.session import Session
from simultradia.domain.entities.cotizacion_entity import PanelMercado
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.domain.enums import LadoOrden, TipoOrden
from simultradia.iu.operar.operar_controller import OperarController
from simultradia.services.operar_service import (
    EstadoOperar, ResultadoCierre, ResultadoOrden, SolicitudOrden)
from tests.fakes import EjecutorDiferido, ServicioGenerico, VistaPanelFalsa, en_el_acto

_HILO = "simultradia.iu.base.panel_controller.ejecutar_en_hilo"


class _VistaOperar(VistaPanelFalsa):
    def __init__(self, id_activo=1, cantidad="0,5", lado=LadoOrden.COMPRA, posicion=None, pendiente=None,
                 confirma_orden=True):
        super().__init__(confirma=True)
        self._id_activo, self._cantidad, self._lado = id_activo, cantidad, lado
        self._posicion, self._pendiente, self._confirma_orden = posicion, pendiente, confirma_orden

    def activo_elegido(self): return self._id_activo
    def solicitud(self): return SolicitudOrden(self._lado, TipoOrden.MERCADO, self._cantidad)
    def riesgo_escrito(self): return "1"
    def posicion_elegida(self): return self._posicion
    def orden_pendiente_elegida(self): return self._pendiente
    def confirmar_orden(self): return self._confirma_orden
    def establecer_activos(self, items): self.eventos.append(("activos", items))
    def seleccionar_activo(self, id_activo): self.eventos.append(("seleccionar", id_activo))
    def establecer_cantidad(self, cantidad): self.eventos.append(("cantidad", cantidad))
    def mostrar_resumen(self, resumen): self.eventos.append(("resumen", resumen))
    def mostrar_estimacion(self, estimacion): self.eventos.append(("estimacion", estimacion))
    def mostrar_error_estimacion(self, texto): self.eventos.append(("error_estimacion", texto))
    def mostrar_posiciones(self, posiciones): self.eventos.append(("posiciones", posiciones))
    def mostrar_pendientes(self, ordenes): self.eventos.append(("pendientes", ordenes))
    def mostrar_historial(self, ordenes): self.eventos.append(("historial", ordenes))
    def mostrar_ejecucion(self, ejecucion): self.eventos.append(("ejecucion", ejecucion))
    def mostrar_pendiente(self, orden): self.eventos.append(("pendiente", orden))
    def mostrar_stop_sugerido(self, sugerencia): self.eventos.append(("stop", sugerencia))
    def mostrar_cantidad_por_riesgo(self, resultado): self.eventos.append(("cantidad_por_riesgo", resultado))
    def mostrar_errores_proteccion(self, errores): self.eventos.append(("errores_proteccion", dict(errores)))
    def limpiar_errores_proteccion(self): self.eventos.append(("limpiar_errores_proteccion", ()))
    def cerrar_proteccion(self): self.eventos.append(("cerrar_proteccion", ()))


def _estado(resumen="RES"):
    return EstadoOperar(resumen, ["P"], ["PEN"], ["H"], D("10000"))


class PruebasOperarController(unittest.TestCase):
    def setUp(self):
        parche = mock.patch(_HILO, en_el_acto)
        parche.start()
        self.addCleanup(parche.stop)
        self.session = Session()
        self.ana = Usuario("Ana", "a@x.com", "h", id_usuario=2)
        self.session.iniciar(self.ana)
        self.elegidos = []

    def _crear(self, vista=None, **respuestas):
        vista = vista or _VistaOperar()
        base = dict(obtener_estado=_estado(), estimar="EST", cantidad_para=D("0.5"),
                    enviar=ResultadoOrden(ejecucion="EJEC"), vender_todo="EJEC", cancelar_orden=None,
                    editar_proteccion=None, cerrar_todas=ResultadoCierre(2, []), sugerir_stop="STOP",
                    cantidad_por_riesgo="CALCULO")
        base.update(respuestas)
        operar = ServicioGenerico(**base)
        mercado = ServicioGenerico(obtener_panel=PanelMercado(items=["A"]))
        controlador = OperarController(vista, operar, mercado, self.session, self.elegidos.append)
        return vista, operar, controlador

    def _cargado(self, vista=None, **respuestas):
        vista, operar, controlador = self._crear(vista, **respuestas)
        controlador.cargar()
        vista.eventos.clear()
        operar.llamadas.clear()
        return vista, operar, controlador

    def _llamadas(self, operar):
        return {c[0] for c in operar.llamadas}

    # ------------------------------------------------------------------ carga
    def test_cargar_muestra_todo_avisa_al_grafico_y_programa_el_refresco(self):
        vista, operar, controlador = self._crear()
        controlador.cargar()
        self.assertEqual(vista.ultimo("activos"), ["A"])
        self.assertEqual((vista.ultimo("resumen"), vista.ultimo("posiciones"), vista.ultimo("pendientes"),
                          vista.ultimo("historial")), ("RES", ["P"], ["PEN"], ["H"]))
        self.assertEqual(operar.llamadas[0], ("obtener_estado", self.ana, 1))
        self.assertEqual(self.elegidos, [1])
        self.assertEqual([ms for ms, _ in vista.programadas], [3000])

    def test_se_puede_abrir_con_un_activo_ya_elegido(self):
        vista, _, controlador = self._crear()
        controlador.cargar(id_activo=5)
        self.assertEqual(vista.ultimo("seleccionar"), 5)

    def test_cada_ciclo_pide_el_estado_completo_en_una_sola_llamada(self):
        vista, operar, _ = self._cargado()
        vista.programadas[-1][1]()
        self.assertEqual(operar.llamadas[0], ("obtener_estado", self.ana, 1))
        self.assertEqual([c[0] for c in operar.llamadas].count("obtener_estado"), 1)

    def test_sin_activo_elegido_igual_se_muestran_posiciones_y_ordenes(self):
        vista = _VistaOperar(id_activo=None)
        operar = ServicioGenerico(obtener_estado=_estado(resumen=None))
        OperarController(vista, operar, ServicioGenerico(obtener_panel=PanelMercado(items=[])), self.session,
                         self.elegidos.append).cargar()
        self.assertEqual(vista.ultimo("posiciones"), ["P"])
        self.assertIsNone(vista.ultimo("resumen"))
        self.assertEqual(self.elegidos, [])

    # ------------------------------------------------------------- estimación
    def test_al_llegar_el_estado_se_estima_la_cantidad_escrita(self):
        vista, operar, _ = self._crear()
        vista.acciones["al_elegir_activo"]()
        self.assertEqual(vista.ultimo("estimacion"), "EST")
        self.assertEqual(operar.llamadas[-1][0], "estimar")

    def test_sin_cantidad_no_hay_estimacion(self):
        vista, operar, _ = self._crear(_VistaOperar(cantidad="  "))
        vista.acciones["al_elegir_activo"]()
        self.assertIsNone(vista.ultimo("estimacion"))
        self.assertNotIn("estimar", self._llamadas(operar))

    def test_cambiar_cantidad_lado_o_tipo_recalcula(self):
        vista, _, _ = self._cargado()
        vista.acciones["al_cambiar_orden"]()
        self.assertEqual(vista.ultimo("estimacion"), "EST")

    def test_un_error_de_la_estimacion_se_muestra_junto_al_ticket(self):
        vista, _, _ = self._crear(estimar=ErrorOperacionInvalida("Saldo insuficiente."))
        vista.acciones["al_elegir_activo"]()
        self.assertEqual(vista.ultimo("error_estimacion"), "Saldo insuficiente.")
        self.assertIsNone(vista.error)

    def test_elegir_otro_activo_avisa_al_grafico_y_pide_el_estado(self):
        vista, operar, _ = self._cargado()
        vista.acciones["al_elegir_activo"]()
        self.assertEqual(self.elegidos[-1], 1)
        self.assertIn("obtener_estado", self._llamadas(operar))

    # -------------------------------------------------------------- porcentaje
    def test_el_porcentaje_rellena_la_cantidad(self):
        vista, operar, _ = self._cargado()
        vista.acciones["al_porcentaje"](50)
        self.assertEqual(operar.llamadas[0][0:1] + operar.llamadas[0][1:2] + operar.llamadas[0][3:], ("cantidad_para", "RES", 50))
        self.assertEqual(vista.ultimo("cantidad"), D("0.5"))

    def test_si_no_hay_nada_que_usar_muestra_el_error(self):
        vista, _, _ = self._cargado(cantidad_para=ErrorOperacionInvalida("No tienes saldo suficiente para comprar."))
        vista.acciones["al_porcentaje"](25)
        self.assertEqual(vista.error, "No tienes saldo suficiente para comprar.")
        self.assertIsNone(vista.ultimo("cantidad"))

    def test_el_porcentaje_espera_a_tener_datos_del_activo(self):
        vista, operar, _ = self._crear()
        vista.acciones["al_porcentaje"](50)
        self.assertEqual(operar.llamadas, [])

    # ------------------------------------------------------------------ enviar
    def test_enviar_valida_confirma_envia_y_refresca(self):
        vista, operar, _ = self._cargado()
        vista.acciones["al_enviar"]()
        self.assertEqual(operar.llamadas[0][0], "estimar")
        enviar = next(c for c in operar.llamadas if c[0] == "enviar")
        self.assertEqual((enviar[1], enviar[2], enviar[3].lado, enviar[3].cantidad), (self.ana, 1, LadoOrden.COMPRA, "0,5"))
        self.assertEqual(vista.ultimo("ejecucion"), "EJEC")
        self.assertFalse(vista.ocupado)
        self.assertIn("obtener_estado", self._llamadas(operar))

    def test_una_orden_limite_se_muestra_como_pendiente(self):
        vista, _, _ = self._cargado(enviar=ResultadoOrden(pendiente="ORDEN"))
        vista.acciones["al_enviar"]()
        self.assertEqual(vista.ultimo("pendiente"), "ORDEN")
        self.assertIsNone(vista.ultimo("ejecucion"))

    def test_si_no_se_confirma_no_se_envia(self):
        vista, operar, _ = self._cargado(_VistaOperar(confirma_orden=False))
        vista.acciones["al_enviar"]()
        self.assertNotIn("enviar", self._llamadas(operar))
        self.assertIsNone(vista.ultimo("ejecucion"))

    def test_un_error_de_validacion_sale_antes_de_confirmar_y_no_envia(self):
        vista, operar, _ = self._cargado(estimar=ErrorOperacionInvalida("Saldo insuficiente."))
        vista.acciones["al_enviar"]()
        self.assertEqual(vista.error, "Saldo insuficiente.")
        self.assertNotIn("enviar", self._llamadas(operar))

    def test_un_error_al_enviar_se_muestra_y_libera_el_boton(self):
        vista, _, _ = self._cargado(enviar=ErrorOperacionInvalida("Ese activo todavía no tiene precio."))
        vista.acciones["al_enviar"]()
        self.assertEqual((vista.error, vista.ocupado), ("Ese activo todavía no tiene precio.", False))
        self.assertIsNone(vista.ultimo("ejecucion"))

    def test_ignora_pulsaciones_mientras_hay_una_orden_en_curso(self):
        vista, operar, _ = self._cargado(_VistaOperar(posicion=7, pendiente=3))
        vista.ocupado = True
        for accion in ("al_enviar", "al_cerrar_posicion", "al_cerrar_todas", "al_cancelar_orden"):
            vista.acciones[accion]()
        self.assertEqual(operar.llamadas, [])

    def test_sin_activo_elegido_o_sin_datos_no_envia_nada(self):
        vista, operar, _ = self._crear(_VistaOperar(id_activo=None))
        vista.acciones["al_enviar"]()
        self.assertEqual(operar.llamadas, [])
        vista, operar, _ = self._crear()                      # hay activo, pero el estado no ha llegado
        vista.acciones["al_enviar"]()
        self.assertEqual(operar.llamadas, [])
        self.assertIn("Espera", vista.error)

    # ------------------------------------------------------------------ cierres
    def test_cerrar_una_posicion_pide_confirmacion_y_vende_todo(self):
        vista, operar, _ = self._cargado(_VistaOperar(posicion=7))
        vista.acciones["al_cerrar_posicion"]()
        self.assertIn(("vender_todo", self.ana, 7), operar.llamadas)
        self.assertEqual(vista.ultimo("ejecucion"), "EJEC")

    def test_cerrar_sin_confirmar_o_sin_elegir_no_hace_nada(self):
        vista, operar, _ = self._cargado(_VistaOperar(posicion=7))
        vista._confirma = False
        vista.acciones["al_cerrar_posicion"]()
        vista, operar, _ = self._cargado(_VistaOperar(posicion=None))
        vista.acciones["al_cerrar_posicion"]()
        self.assertNotIn("vender_todo", self._llamadas(operar))

    def test_cerrar_todas(self):
        vista, operar, _ = self._cargado()
        vista.acciones["al_cerrar_todas"]()
        self.assertIn("cerrar_todas", self._llamadas(operar))
        self.assertIn("2", vista.exito)
        self.assertFalse(vista.ocupado)

    def test_cerrar_todas_con_fallos_los_lista(self):
        vista, _, _ = self._cargado(cerrar_todas=ResultadoCierre(1, ["XYZ: sin precio"]))
        vista.acciones["al_cerrar_todas"]()
        self.assertIn("XYZ: sin precio", vista.error)

    def test_cerrar_todas_sin_confirmar_no_hace_nada(self):
        vista, operar, _ = self._cargado()
        vista._confirma = False
        vista.acciones["al_cerrar_todas"]()
        self.assertNotIn("cerrar_todas", self._llamadas(operar))

    # ------------------------------------------------------------ pendientes
    def test_cancelar_una_orden_pendiente(self):
        vista, operar, _ = self._cargado(_VistaOperar(pendiente=3))
        vista.acciones["al_cancelar_orden"]()
        self.assertIn(("cancelar_orden", self.ana, 3), operar.llamadas)
        self.assertEqual(vista.exito, "Orden cancelada.")
        self.assertIn("obtener_estado", self._llamadas(operar))

    def test_cancelar_sin_confirmar_o_sin_elegir_no_hace_nada(self):
        vista, operar, _ = self._cargado(_VistaOperar(pendiente=3))
        vista._confirma = False
        vista.acciones["al_cancelar_orden"]()
        vista, operar2, _ = self._cargado(_VistaOperar(pendiente=None))
        vista.acciones["al_cancelar_orden"]()
        self.assertNotIn("cancelar_orden", self._llamadas(operar) | self._llamadas(operar2))

    # ------------------------------------------------- stop-loss y take-profit
    def test_guardar_la_proteccion_cierra_la_ventana_y_refresca(self):
        vista, operar, _ = self._cargado()
        vista.acciones["al_guardar_proteccion"](1, "90", "120")
        self.assertIn(("editar_proteccion", self.ana, 1, "90", "120"), operar.llamadas)
        self.assertIsNotNone(vista.ultimo("cerrar_proteccion"))
        self.assertIn("guardados", vista.exito)
        self.assertIn("obtener_estado", self._llamadas(operar))

    def test_los_errores_de_la_proteccion_van_a_su_campo_dentro_de_la_ventana(self):
        vista, _, _ = self._cargado(editar_proteccion=DatosInvalidos({"stop_loss": "Debe estar por debajo."}))
        vista.acciones["al_guardar_proteccion"](1, "150", "")
        self.assertEqual(vista.ultimo("errores_proteccion"), {"stop_loss": "Debe estar por debajo."})
        self.assertIsNone(vista.ultimo("cerrar_proteccion"))
        self.assertIsNone(vista.error)

    def test_otro_error_de_la_proteccion_va_al_mensaje_general(self):
        vista, _, _ = self._cargado(editar_proteccion=ErrorOperacionInvalida("No tienes este activo."))
        vista.acciones["al_guardar_proteccion"](1, "90", "")
        self.assertEqual(vista.error, "No tienes este activo.")

    # ------------------------------------------------------ calculadora de riesgo
    def test_sugerir_stop_pide_el_stop_y_lo_muestra(self):
        vista, operar, _ = self._cargado()
        vista.acciones["al_sugerir_stop"]()
        llamada = operar.llamadas[0]
        self.assertEqual((llamada[0], llamada[1], llamada[2]), ("sugerir_stop", self.ana, 1))
        self.assertEqual(vista.ultimo("stop"), "STOP")

    def test_un_error_al_sugerir_el_stop_se_muestra(self):
        vista, _, _ = self._cargado(sugerir_stop=ErrorOperacionInvalida("Sin velas suficientes."))
        vista.acciones["al_sugerir_stop"]()
        self.assertEqual(vista.error, "Sin velas suficientes.")
        self.assertIsNone(vista.ultimo("stop"))

    def test_sugerir_stop_sin_activo_elegido_no_hace_nada(self):
        vista, operar, _ = self._cargado(_VistaOperar(id_activo=None))
        vista.acciones["al_sugerir_stop"]()
        self.assertEqual(operar.llamadas, [])

    def test_calcular_la_cantidad_usa_el_riesgo_escrito_y_el_patrimonio(self):
        vista, operar, _ = self._cargado()
        vista.acciones["al_calcular_cantidad"]()
        llamada = operar.llamadas[0]
        self.assertEqual((llamada[0], llamada[1], llamada[3], llamada[4]), ("cantidad_por_riesgo", "RES", "1", D("10000")))
        self.assertEqual(vista.ultimo("cantidad_por_riesgo"), "CALCULO")

    def test_un_error_al_calcular_la_cantidad_se_muestra(self):
        vista, _, _ = self._cargado(cantidad_por_riesgo=DatosInvalidos({"stop_loss": "Pon primero un stop-loss."}))
        vista.acciones["al_calcular_cantidad"]()
        self.assertEqual(vista.error, "Pon primero un stop-loss.")
        self.assertIsNone(vista.ultimo("cantidad_por_riesgo"))

    def test_calcular_espera_a_tener_datos_del_activo(self):
        vista, operar, _ = self._crear()
        vista.acciones["al_calcular_cantidad"]()
        self.assertEqual([c for c in operar.llamadas if c[0] == "cantidad_por_riesgo"], [])

    def test_la_estimacion_recibe_el_patrimonio(self):
        vista, operar, _ = self._cargado()
        vista.acciones["al_cambiar_orden"]()
        self.assertEqual(operar.llamadas[-1][3], D("10000"))

    # ------------------------------------------------------------ respuestas tardías
    def test_un_estado_viejo_se_descarta(self):
        vista, _, _ = self._crear()
        ejecutor = EjecutorDiferido()
        with mock.patch(_HILO, ejecutor):
            vista.acciones["al_elegir_activo"]()
            vista.acciones["al_elegir_activo"]()
            ejecutor.terminar_todo()
        self.assertEqual(len([e for e in vista.eventos if e[0] == "resumen"]), 1)

    def test_si_la_pantalla_ya_no_existe_no_la_toca_ni_programa_mas(self):
        vista, _, controlador = self._crear()
        vista.viva = False
        controlador.cargar()
        self.assertEqual(([e for e in vista.eventos if e[0] != "estimacion"], vista.programadas), ([], []))


if __name__ == "__main__":
    unittest.main()
