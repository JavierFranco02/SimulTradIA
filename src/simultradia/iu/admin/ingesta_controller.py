"""Controlador de Administración · Ingesta: muestra el estado (se refresca solo), habilita fuentes
y lanza la actualización manual."""
from simultradia.iu.base.panel_controller import PanelController

_CADA_MS = 5000


class IngestaController(PanelController):
    def __init__(self, vista, ingesta_service, fuente_admin_service, session):
        super().__init__(vista)
        self._ingesta = ingesta_service
        self._fuentes = fuente_admin_service
        self._session = session
        vista.vincular_acciones(al_actualizar=self.actualizar_ahora, al_cambiar_fuente=self.cambiar_fuente,
                                al_probar_fuente=self.probar_fuente, al_actualizar_fuente=self.actualizar_fuente)

    def cargar(self) -> None:
        self._ciclo()

    def actualizar_ahora(self) -> None:
        if self._vista.ocupado:
            return
        actor = self._session.usuario
        self._vista.limpiar_mensaje()
        self._vista.establecer_ocupado(True)
        self._ejecutar(lambda: self._ingesta.ejecutar_manual(actor),
                       al_terminar=self._al_terminar_manual, al_fallar=self._al_fallar_manual)

    def actualizar_fuente(self, id_fuente: int) -> None:
        """Actualiza solo los activos de una fuente (la elegida en la tabla)."""
        if self._vista.ocupado:
            return
        actor = self._session.usuario
        self._vista.limpiar_mensaje()
        self._vista.establecer_ocupado(True)
        self._ejecutar(lambda: self._ingesta.ejecutar_manual(actor, id_fuente),
                       al_terminar=self._al_terminar_manual, al_fallar=self._al_fallar_manual)

    def probar_fuente(self, id_fuente: int) -> None:
        """Comprueba que la fuente responde y cuánto tarda. No guarda nada."""
        if self._vista.ocupado:
            return
        actor = self._session.usuario
        self._vista.limpiar_mensaje()
        self._vista.establecer_ocupado(True)
        self._ejecutar(lambda: self._ingesta.probar_fuente(actor, id_fuente),
                       al_terminar=self._al_probar, al_fallar=self._al_fallar_manual)

    def cambiar_fuente(self, id_fuente: int, activar: bool) -> None:
        if not activar and not self._vista.confirmar(
                "¿Deshabilitar esta fuente? Sus activos dejarán de actualizarse."):
            return
        actor = self._session.usuario
        self._vista.limpiar_mensaje()
        self._ejecutar(lambda: self._fuentes.cambiar_estado(actor, id_fuente, activar),
                       al_terminar=lambda _resultado: self._pedir_estado())

    # --------------------------------------------------------------- interno
    def _ciclo(self) -> None:
        if not self._vista.esta_viva():
            return
        self._pedir_estado()
        self._vista.programar(_CADA_MS, self._ciclo)

    def _pedir_estado(self) -> None:
        actor = self._session.usuario
        self._ejecutar(lambda: (self._ingesta.obtener_estado(actor), self._fuentes.listar(actor)),
                       al_terminar=lambda resultado: self._vista.mostrar_estado(*resultado))

    def _al_terminar_manual(self, resultado) -> None:
        self._vista.establecer_ocupado(False)
        if resultado.fallidos:
            self._vista.mostrar_error("Terminó con %d error(es): %s" % (
                len(resultado.fallidos), ", ".join(resultado.fallidos[:6])
                + ("…" if len(resultado.fallidos) > 6 else "")))
        else:
            self._vista.mostrar_exito("Listo: %d actualizaciones correctas." % resultado.correctos)
        self._pedir_estado()

    def _al_probar(self, resultado) -> None:
        self._vista.establecer_ocupado(False)
        if resultado.ok:
            self._vista.mostrar_exito("%s: %s (%d ms)" % (resultado.fuente, resultado.mensaje, resultado.milisegundos))
        else:
            self._vista.mostrar_error("%s no responde: %s" % (resultado.fuente, resultado.mensaje))

    def _al_fallar_manual(self, error: Exception) -> None:
        self._vista.establecer_ocupado(False)
        self._al_fallar(error)
