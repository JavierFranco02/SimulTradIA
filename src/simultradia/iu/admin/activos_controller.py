"""Controlador de Administración · Activos: buscar, agregar, probar, editar, habilitar y cambiar la fuente."""
from simultradia.core.exceptions import DatosInvalidos
from simultradia.iu.base.panel_controller import PanelController


class ActivosAdminController(PanelController):
    def __init__(self, vista, activo_admin_service, fuente_admin_service, session):
        super().__init__(vista)
        self._activos = activo_admin_service
        self._fuentes = fuente_admin_service
        self._session = session
        self._solicitud = 0    # número de la última petición: las respuestas viejas se descartan
        vista.vincular_acciones(
            al_agregar=self.agregar, al_cambiar_estado=self.cambiar_estado,
            al_cambiar_fuente=self.cambiar_fuente, al_probar_ticker=self.probar_ticker,
            al_probar_fuente=self.probar_fuente, al_filtrar=self.cargar, al_editar=self.editar)

    def cargar(self) -> None:
        self._solicitud += 1
        numero, actor = self._solicitud, self._session.usuario
        texto, tipo, habilitado = self._vista.filtros()
        self._ejecutar(
            lambda: (self._activos.listar(actor, texto, tipo, habilitado), self._fuentes.listar(actor)),
            al_terminar=lambda resultado: self._al_cargar(numero, resultado))

    def agregar(self) -> None:
        if self._vista.ocupado:
            return   # ya hay un intento en curso
        datos = self._vista.valores()
        actor = self._session.usuario
        id_fuente = int(datos["fuente"]) if datos["fuente"] else 0
        self._vista.limpiar_errores()
        self._vista.establecer_ocupado(True)
        self._ejecutar(
            lambda: self._activos.agregar(actor, datos["ticker"], datos["nombre"], datos["tipo"], id_fuente),
            al_terminar=self._al_agregar, al_fallar=self._al_fallar_agregar)

    def probar_ticker(self) -> None:
        """Comprueba, sin agregar nada, que la fuente elegida reconoce el ticker escrito."""
        if self._vista.ocupado:
            return
        datos = self._vista.valores()
        actor = self._session.usuario
        id_fuente = int(datos["fuente"]) if datos["fuente"] else 0
        self._vista.limpiar_errores()
        self._vista.establecer_ocupado(True)
        self._ejecutar(
            lambda: self._activos.probar_ticker(actor, datos["ticker"], datos["tipo"], id_fuente),
            al_terminar=lambda fuente: self._al_probar(fuente, datos["ticker"]),
            al_fallar=self._al_fallar_agregar)

    def probar_fuente(self, ticker: str, tipo: str, id_fuente: int) -> None:
        """Comprueba que la fuente elegida en "Pasar a" reconoce el ticker del activo elegido."""
        actor = self._session.usuario
        self._vista.limpiar_mensaje()
        self._ejecutar(
            lambda: self._activos.probar_ticker(actor, ticker, tipo, id_fuente),
            al_terminar=lambda fuente: self._vista.mostrar_exito("✓ %s reconoce %s." % (fuente, ticker.upper())),
            al_fallar=self._al_fallar_prueba)

    def editar(self, id_activo: int, nombre: str, moneda: str) -> None:
        actor = self._session.usuario
        self._vista.limpiar_mensaje()
        self._vista.limpiar_errores_edicion()
        self._ejecutar(lambda: self._activos.editar(actor, id_activo, nombre, moneda),
                       al_terminar=self._al_editar, al_fallar=self._al_fallar_edicion)

    def cambiar_estado(self, id_activo: int, habilitar: bool) -> None:
        actor = self._session.usuario
        self._vista.limpiar_mensaje()
        self._ejecutar(lambda: self._activos.cambiar_estado(actor, id_activo, habilitar),
                       al_terminar=lambda _resultado: self.cargar())

    def cambiar_fuente(self, id_activo: int, id_fuente: int) -> None:
        if not self._vista.confirmar("¿Cambiar la fuente de este activo? Se borrarán sus velas "
                                     "guardadas y se descargarán de nuevo desde la fuente nueva."):
            return
        actor = self._session.usuario
        self._vista.limpiar_mensaje()
        self._ejecutar(lambda: self._activos.cambiar_fuente(actor, id_activo, id_fuente),
                       al_terminar=lambda _resultado: self.cargar())

    # --------------------------------------------------------------- interno
    def _al_cargar(self, numero: int, resultado) -> None:
        if numero != self._solicitud:
            return
        items, fuentes = resultado
        self._vista.establecer_fuentes(fuentes)
        self._vista.mostrar_activos(items)

    def _al_agregar(self, activo) -> None:
        self._vista.establecer_ocupado(False)
        self._vista.limpiar_formulario()      # cierra la ventana de agregar
        self._vista.mostrar_exito("%s agregado. Sus velas se descargan en la próxima pasada del worker."
                                  % activo.ticker)
        self.cargar()

    def _al_probar(self, fuente: str, ticker: str) -> None:
        self._vista.establecer_ocupado(False)
        self._vista.mostrar_exito("✓ %s reconoce %s." % (fuente, ticker.strip().upper()))

    def _al_editar(self, _resultado) -> None:
        self._vista.cerrar_edicion()
        self._vista.mostrar_exito("Cambios guardados.")
        self.cargar()

    def _al_fallar_agregar(self, error: Exception) -> None:
        self._vista.establecer_ocupado(False)
        if isinstance(error, DatosInvalidos):
            self._vista.mostrar_errores_campos(error.errores)   # cada mensaje bajo su campo
        else:
            self._al_fallar(error)

    def _al_fallar_prueba(self, error: Exception) -> None:
        # Aquí no hay campos del formulario de alta: el motivo se muestra como mensaje general.
        self._al_fallar(error)

    def _al_fallar_edicion(self, error: Exception) -> None:
        if isinstance(error, DatosInvalidos):
            self._vista.mostrar_errores_edicion(error.errores)
        else:
            self._al_fallar(error)
