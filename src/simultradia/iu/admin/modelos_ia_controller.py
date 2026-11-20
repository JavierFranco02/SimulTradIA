"""Controlador de Administración · Modelos de IA.

  - Muestra las versiones y el estado del ciclo (se refresca solo cada pocos segundos).
  - «Entrenar y evaluar» y «Comparar algoritmos» tardan minutos: corren en segundo plano, con los botones quietos,
    y al terminar avisan con un diálogo. Si el administrador sale de la pantalla, el entrenamiento igual termina y se guarda.
  - «Activar» vuelve a poner activa una versión archivada que supera la base.
"""
from simultradia.domain.reglas.prediccion import HORIZONTE
from simultradia.iu.base.panel_controller import PanelController
from simultradia.iu.ia import textos

_CADA_MS = 10000


def texto_resultado(resultado) -> str:
    """Qué pasó con un entrenamiento, en una frase."""
    m, ev = resultado.modelo, resultado.evaluacion
    base = "%s %s: %s (z = %s)." % (m.nombre, m.version, ev.veredicto.lower(), textos.numero(ev.z))
    if resultado.activado:
        return base + " Quedó activo."
    return base + " No se activó: sigue el modelo anterior, si había."


class ModelosIAController(PanelController):
    def __init__(self, vista, modelo_ia_service, prediccion_service, session):
        super().__init__(vista)
        self._modelos = modelo_ia_service
        self._predicciones = prediccion_service
        self._session = session
        vista.vincular_acciones(al_entrenar=self.entrenar, al_comparar=self.comparar, al_activar=self.activar)

    def cargar(self) -> None:
        self._ciclo()

    def entrenar(self) -> None:
        if self._vista.ocupado:
            return
        if not self._vista.confirmar("Entrenar lee todo el historial y puede tardar varios minutos. ¿Continuar?"):
            return
        actor = self._session.usuario
        self._vista.establecer_ocupado(True, "entrenar")
        self._ejecutar(lambda: self._modelos.entrenar(actor, HORIZONTE),
                       al_terminar=self._al_entrenar, al_fallar=self._al_fallar_accion)

    def comparar(self) -> None:
        if self._vista.ocupado:
            return
        actor = self._session.usuario
        self._vista.establecer_ocupado(True, "comparar")
        self._ejecutar(lambda: self._modelos.comparar(actor, HORIZONTE),
                       al_terminar=self._al_comparar,
                       al_fallar=self._al_fallar_accion)

    def activar(self, id_modelo: int) -> None:
        if self._vista.ocupado:
            return
        if not self._vista.confirmar("¿Activar esta versión? Reemplaza a la que está activa."):
            return
        actor = self._session.usuario
        self._ejecutar(lambda: self._modelos.activar(actor, id_modelo),
                       al_terminar=lambda _r: self._pedir_estado())

    # --------------------------------------------------------------- interno
    def _ciclo(self) -> None:
        if not self._vista.esta_viva():
            return
        self._pedir_estado()
        self._vista.programar(_CADA_MS, self._ciclo)

    def _pedir_estado(self) -> None:
        actor = self._session.usuario
        self._ejecutar(lambda: (self._modelos.listar(actor), self._predicciones.estado_ciclo(actor)),
                       al_terminar=self._al_estado,
                       al_fallar=lambda error: self._avisar_una_vez("estado", error))

    def _al_estado(self, resultado) -> None:
        self._recuperado("estado")
        self._vista.mostrar_estado(*resultado)

    def _al_entrenar(self, resultado) -> None:
        self._vista.establecer_ocupado(False)
        self._vista.mostrar_exito(texto_resultado(resultado))
        self._pedir_estado()

    def _al_comparar(self, filas) -> None:
        self._vista.establecer_ocupado(False)
        self._vista.mostrar_comparacion([(c.algoritmo, c.evaluacion) for c in filas])

    def _al_fallar_accion(self, error: Exception) -> None:
        self._vista.establecer_ocupado(False)
        self._al_fallar(error)
        self._pedir_estado()        # el entrenamiento fallido queda registrado como versión «Fallido»
