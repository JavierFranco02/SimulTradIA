"""Controlador de «Predicciones IA».

  - Al abrir y cada minuto pide el resumen del horizonte (modelo activo, escáner y acierto real): las predicciones
    cambian una vez al día, no hace falta más.
  - Elegir un activo pide su detalle (factores e historial) y su proyección; si en un refresco la predicción
    vigente de ese activo cambió (empezó otro día), el detalle se vuelve a pedir solo.
  - Cambiar de horizonte o de activo descarta las respuestas que llegan tarde.
  - Cuando no hay activo elegido (al abrir, o al cambiar de horizonte) elige el mismo de antes si sigue en el
    escáner, o el de más confianza: la pantalla no empieza vacía.
"""
from typing import Optional

from simultradia.core.exceptions import ErrorAplicacion
from simultradia.domain.reglas.prediccion import HORIZONTE_INICIAL
from simultradia.iu.base.panel_controller import PanelController

_CADA_MS = 60000
_DIAS_MINIMOS_PROYECCION = 5


class IAController(PanelController):
    def __init__(self, vista, prediccion_service):
        super().__init__(vista)
        self._servicio = prediccion_service
        self._horizonte = HORIZONTE_INICIAL
        self._id_activo: Optional[int] = None
        self._id_prediccion: Optional[int] = None      # la predicción vigente que muestra el detalle
        self._nivel: Optional[float] = None
        self._peticion_resumen = 0
        self._peticion_detalle = 0
        self._peticion_proyeccion = 0
        self._preferido: Optional[int] = None         # el activo que había antes de cambiar de horizonte
        vista.vincular_acciones(al_elegir_horizonte=self.elegir_horizonte,
                                al_elegir_activo=self.elegir_activo,
                                al_calcular_nivel=self.calcular_nivel)

    def cargar(self) -> None:
        self._ciclo()

    def elegir_horizonte(self, horizonte: int) -> None:
        if horizonte == self._horizonte:
            return
        self._horizonte = horizonte
        self._preferido = self._id_activo
        self._id_activo = self._id_prediccion = None
        self._peticion_detalle += 1                  # lo que venga del horizonte anterior ya no vale
        self._peticion_proyeccion += 1
        self._vista.limpiar_detalle()
        self._pedir_resumen()

    def elegir_activo(self, id_activo: int) -> None:
        if id_activo == self._id_activo:
            return
        self._id_activo = id_activo
        self._id_prediccion = None
        self._pedir_detalle()
        self._pedir_proyeccion()

    def calcular_nivel(self) -> None:
        texto = self._vista.texto_nivel().strip().replace(" ", "").replace(",", ".")
        if texto:
            try:
                nivel = float(texto)
            except ValueError:
                self._vista.mostrar_error("Escribe el nivel como un número, por ejemplo 150,5.")
                return
            if nivel <= 0:
                self._vista.mostrar_error("El nivel debe ser mayor que cero.")
                return
            self._nivel = nivel
        else:
            self._nivel = None
        if self._id_activo is not None:
            self._pedir_proyeccion()

    # --------------------------------------------------------------- interno
    def _ciclo(self) -> None:
        if not self._vista.esta_viva():
            return
        self._pedir_resumen()
        self._vista.programar(_CADA_MS, self._ciclo)

    def _pedir_resumen(self) -> None:
        self._peticion_resumen += 1
        numero, horizonte = self._peticion_resumen, self._horizonte
        self._ejecutar(lambda: self._servicio.resumen(horizonte),
                       al_terminar=lambda resumen: self._al_resumen(numero, resumen),
                       al_fallar=lambda error: self._avisar_una_vez("resumen", error))

    def _al_resumen(self, numero: int, resumen) -> None:
        if numero != self._peticion_resumen:
            return
        self._recuperado("resumen")
        self._vista.mostrar_resumen(resumen)
        if self._id_activo is not None:
            vigente = next((s.prediccion for s in resumen.senales if s.prediccion.id_activo == self._id_activo), None)
            nueva = vigente.id_prediccion if vigente else None
            if self._id_prediccion is not None and nueva != self._id_prediccion:
                self._pedir_detalle()                # empezó otro día: el detalle mostrado quedó viejo
        elif resumen.senales:
            ids = [s.prediccion.id_activo for s in resumen.senales]
            elegido = self._preferido if self._preferido in ids else ids[0]
            self.elegir_activo(elegido)
            self._vista.seleccionar(elegido)

    def _pedir_detalle(self) -> None:
        self._peticion_detalle += 1
        numero, id_activo, horizonte = self._peticion_detalle, self._id_activo, self._horizonte
        self._ejecutar(lambda: self._servicio.detalle(id_activo, horizonte),
                       al_terminar=lambda detalle: self._al_detalle(numero, id_activo, horizonte, detalle),
                       al_fallar=lambda error: self._avisar_una_vez("detalle", error))

    def _al_detalle(self, numero: int, id_activo: int, horizonte: int, detalle) -> None:
        if numero != self._peticion_detalle:
            return
        self._recuperado("detalle")
        self._id_prediccion = detalle.vigente.id_prediccion if detalle.vigente else None
        ticker, nombre = self._vista.datos_de(id_activo)
        self._vista.mostrar_detalle(ticker, nombre, horizonte, detalle)

    def _pedir_proyeccion(self) -> None:
        self._peticion_proyeccion += 1
        numero, id_activo = self._peticion_proyeccion, self._id_activo
        dias, nivel = max(self._horizonte, _DIAS_MINIMOS_PROYECCION), self._nivel
        self._ejecutar(lambda: self._servicio.proyectar(id_activo, dias, nivel),
                       al_terminar=lambda proyeccion: self._al_proyeccion(numero, nivel, proyeccion),
                       al_fallar=lambda error: self._al_fallar_proyeccion(numero, error))

    def _al_proyeccion(self, numero: int, nivel: Optional[float], proyeccion) -> None:
        if numero == self._peticion_proyeccion:
            self._vista.mostrar_proyeccion(proyeccion, nivel)

    def _al_fallar_proyeccion(self, numero: int, error: Exception) -> None:
        if numero != self._peticion_proyeccion:
            return
        if isinstance(error, ErrorAplicacion):          # no es un fallo: al activo le faltan velas
            self._vista.proyeccion_no_disponible(str(error))
        else:
            self._al_fallar(error)
