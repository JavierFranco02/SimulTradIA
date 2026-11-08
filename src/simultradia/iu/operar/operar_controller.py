"""Controlador de Operar: carga los activos, refresca el estado cada pocos segundos y lanza las órdenes.

  - Cada 3 s pide TODO el estado de una vez (resumen del activo elegido, posiciones, órdenes pendientes e
    historial): así el P&L sigue al precio y se ve cuándo el worker ejecuta una orden límite o un stop-loss.
  - La estimación se recalcula al escribir, al cambiar de lado o de tipo y con cada precio nuevo.
  - Antes de enviar una orden se valida y se pide confirmación; mientras se envía no se acepta otra.
  - Cada petición lleva un número: si llega una vieja (el usuario ya eligió otro activo), se descarta.
  - El gráfico es de GraficoController: aquí solo se le avisa qué activo se eligió.
"""
from simultradia.core.exceptions import DatosInvalidos, ErrorAplicacion
from simultradia.iu.base.panel_controller import PanelController

_CADA_MS = 3000


class OperarController(PanelController):
    def __init__(self, vista, operar_service, mercado_service, session, al_elegir_activo):
        """`al_elegir_activo(id_activo)` es quien muestra el gráfico del activo elegido."""
        super().__init__(vista)
        self._servicio = operar_service
        self._mercado = mercado_service
        self._session = session
        self._al_elegir_activo = al_elegir_activo
        self._resumen = None          # lo último que se supo del activo elegido (None mientras llega)
        self._solicitud = 0
        self._id_inicial = None
        vista.vincular_acciones(
            al_elegir_activo=self._elegir, al_cambiar_orden=self._actualizar_estimacion,
            al_porcentaje=self.elegir_porcentaje, al_enviar=self.enviar,
            al_cerrar_posicion=self.cerrar_posicion, al_cerrar_todas=self.cerrar_todas,
            al_guardar_proteccion=self.guardar_proteccion, al_cancelar_orden=self.cancelar_orden)

    def cargar(self, id_activo=None) -> None:
        """Pide la lista de activos; al llegar, muestra todo y empieza el refresco.
        `id_activo` es el activo que se abre ya elegido (por ejemplo, desde Mercado)."""
        self._id_inicial = id_activo
        self._ejecutar(lambda: self._mercado.obtener_panel().items, al_terminar=self._al_cargar_activos)

    def elegir_porcentaje(self, porcentaje: int) -> None:
        """Rellena la cantidad con el 25, 50, 75 o 100 % de lo máximo (saldo al comprar, posición al vender)."""
        if self._resumen is None:
            return
        try:
            self._vista.establecer_cantidad(
                self._servicio.cantidad_para(self._resumen, self._vista.solicitud(), porcentaje))
        except ErrorAplicacion as error:
            self._al_fallar(error)

    def enviar(self) -> None:
        if self._vista.ocupado:
            return   # ya hay una orden en curso
        id_activo = self._vista.activo_elegido()
        if id_activo is None:
            return
        if self._resumen is None:
            self._vista.mostrar_error("Todavía no hay datos de este activo. Espera un momento.")
            return
        solicitud, actor = self._vista.solicitud(), self._session.usuario
        try:
            self._servicio.estimar(self._resumen, solicitud)    # que el error salga ANTES de confirmar
        except ErrorAplicacion as error:
            self._vista.mostrar_error(str(error))
            return
        if not self._vista.confirmar_orden():
            return
        self._lanzar(lambda: self._servicio.enviar(actor, id_activo, solicitud), self._al_enviar)

    def cerrar_posicion(self) -> None:
        id_activo = self._vista.posicion_elegida()
        if id_activo is None or self._vista.ocupado:
            return
        if not self._vista.confirmar("¿Vender toda tu posición de este activo al precio de mercado?"):
            return
        actor = self._session.usuario
        self._lanzar(lambda: self._servicio.vender_todo(actor, id_activo), self._al_cerrar_posicion)

    def cerrar_todas(self) -> None:
        if self._vista.ocupado:
            return
        if not self._vista.confirmar("¿Vender TODAS tus posiciones al precio de mercado?"):
            return
        actor = self._session.usuario
        self._lanzar(lambda: self._servicio.cerrar_todas(actor), self._al_cerrar_todas)

    def cancelar_orden(self) -> None:
        id_orden = self._vista.orden_pendiente_elegida()
        if id_orden is None or self._vista.ocupado:
            return
        if not self._vista.confirmar("¿Cancelar esta orden pendiente?"):
            return
        actor = self._session.usuario
        self._lanzar(lambda: self._servicio.cancelar_orden(actor, id_orden), self._al_cancelar)

    def guardar_proteccion(self, id_activo: int, stop_loss: str, take_profit: str) -> None:
        """Guarda el stop-loss y el take-profit de una posición (los pone la ventana emergente)."""
        actor = self._session.usuario
        self._vista.limpiar_errores_proteccion()
        self._ejecutar(lambda: self._servicio.editar_proteccion(actor, id_activo, stop_loss, take_profit),
                       al_terminar=self._al_proteccion, al_fallar=self._al_fallar_proteccion)

    # --------------------------------------------------------------- interno
    def _al_cargar_activos(self, items) -> None:
        self._vista.establecer_activos(items)
        if self._id_inicial is not None:
            self._vista.seleccionar_activo(self._id_inicial)
        self._elegir()
        self._vista.programar(_CADA_MS, self._ciclo)

    def _ciclo(self) -> None:
        if not self._vista.esta_viva():
            return
        self._pedir_estado()
        self._vista.programar(_CADA_MS, self._ciclo)

    def _elegir(self) -> None:
        """El usuario eligió (o se preeligió) otro activo."""
        self._resumen = None
        self._vista.mostrar_estimacion(None)
        id_activo = self._vista.activo_elegido()
        if id_activo is not None:
            self._al_elegir_activo(id_activo)
        self._pedir_estado()

    def _pedir_estado(self) -> None:
        self._solicitud += 1
        numero, actor, id_activo = self._solicitud, self._session.usuario, self._vista.activo_elegido()
        self._ejecutar(lambda: self._servicio.obtener_estado(actor, id_activo),
                       al_terminar=lambda estado: self._al_estado(numero, estado))

    def _al_estado(self, numero: int, estado) -> None:
        if numero != self._solicitud:
            return
        self._resumen = estado.resumen
        if estado.resumen is not None:
            self._vista.mostrar_resumen(estado.resumen)
        self._vista.mostrar_posiciones(estado.posiciones)
        self._vista.mostrar_pendientes(estado.pendientes)
        self._vista.mostrar_historial(estado.historial)
        self._actualizar_estimacion()

    def _actualizar_estimacion(self) -> None:
        if self._resumen is None or not self._vista.solicitud().cantidad.strip():
            self._vista.mostrar_estimacion(None)
            return
        try:
            estimacion = self._servicio.estimar(self._resumen, self._vista.solicitud())
        except ErrorAplicacion as error:
            self._vista.mostrar_error_estimacion(str(error))
            return
        self._vista.mostrar_estimacion(estimacion)

    def _lanzar(self, trabajo, al_terminar) -> None:
        self._vista.limpiar_mensaje()
        self._vista.establecer_ocupado(True)
        self._ejecutar(trabajo, al_terminar=al_terminar, al_fallar=self._al_fallar_operar)

    def _al_enviar(self, resultado) -> None:
        self._vista.establecer_ocupado(False)
        if resultado.ejecucion is not None:
            self._vista.mostrar_ejecucion(resultado.ejecucion)
        else:
            self._vista.mostrar_pendiente(resultado.pendiente)
        self._pedir_estado()

    def _al_cerrar_posicion(self, ejecucion) -> None:
        self._vista.establecer_ocupado(False)
        self._vista.mostrar_ejecucion(ejecucion)
        self._pedir_estado()

    def _al_cerrar_todas(self, resultado) -> None:
        self._vista.establecer_ocupado(False)
        if resultado.fallidas:
            self._vista.mostrar_error("Se cerraron %d posiciones. No se pudo cerrar: %s"
                                      % (resultado.cerradas, "; ".join(resultado.fallidas)))
        else:
            self._vista.mostrar_exito("Se cerraron %d posiciones." % resultado.cerradas)
        self._pedir_estado()

    def _al_cancelar(self, _resultado) -> None:
        self._vista.establecer_ocupado(False)
        self._vista.mostrar_exito("Orden cancelada.")
        self._pedir_estado()

    def _al_proteccion(self, _resultado) -> None:
        self._vista.cerrar_proteccion()
        self._vista.mostrar_exito("Stop-loss y take-profit guardados.")
        self._pedir_estado()

    def _al_fallar_proteccion(self, error: Exception) -> None:
        if isinstance(error, DatosInvalidos):
            self._vista.mostrar_errores_proteccion(error.errores)   # cada mensaje bajo su campo
        else:
            self._al_fallar(error)

    def _al_fallar_operar(self, error: Exception) -> None:
        self._vista.establecer_ocupado(False)
        self._al_fallar(error)
